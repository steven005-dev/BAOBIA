/**
 * Suite du plan de test : confirmation assistée (MV-04), contestation (MV-09), envoi au
 * retour du réseau (TR-05) et parcours de la démonstration (signalement à A, validation
 * vétérinaire, B et marché en contact possible, D écarté, message neutre à B).
 *
 * Données : base de démo (`seed --demo`, `seed_health`, `seed_alerts`,
 * `seed_demo_traceability`). Le scénario modifie cette base (données simulées).
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const password = process.env.SEED_DEMO_PASSWORD ?? ''
const api = process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000'
const PHONES = {
  breeder1: '0000000001', breeder2: '0000000002', breeder3: '0000000003',
  vet: '0000000004', agent: '0000000005',
}
const DEMO_ANIMAL_CODE = 'KECTT2U8V' // Animal 1, bovin de l'Élevage A (signalement de la démo)

type Center = { id: string; name: string }
type UnitItem = { id: string; kind: string; local_name: string | null; label_code: string | null }

// Un jeton par compte : la connexion est limitée en nombre d'essais (throttling DRF).
const tokens = new Map<string, string>()

async function token(request: APIRequestContext, phone: string) {
  const cached = tokens.get(phone)
  if (cached) return cached
  const response = await request.post(`${api}/api/auth/login/`, { data: { phone, password } })
  expect(response.ok(), `Connexion ${phone} : HTTP ${response.status()}`).toBeTruthy()
  const access = ((await response.json()) as { access: string }).access
  tokens.set(phone, access)
  return access
}

async function call<T>(request: APIRequestContext, phone: string, method: 'GET' | 'POST',
                       path: string, data?: unknown, expected?: number) {
  const headers = { Authorization: `Bearer ${await token(request, phone)}` }
  const response = method === 'GET'
    ? await request.get(`${api}/api${path}`, { headers })
    : await request.post(`${api}/api${path}`, { headers, data })
  const body = await response.text()
  if (expected) expect(response.status(), `${method} ${path} : ${body.slice(0, 300)}`).toBe(expected)
  else expect(response.ok(), `${method} ${path} : ${body.slice(0, 300)}`).toBeTruthy()
  return (body ? JSON.parse(body) : null) as T
}

async function center(request: APIRequestContext, phone: string, name: string) {
  const centers = await call<Center[]>(request, phone, 'GET', '/centers/')
  const found = centers.find((c) => c.name === name)
  expect(found, `${name} visible par ${phone}`).toBeTruthy()
  return found!
}

async function animals(request: APIRequestContext, phone: string, centerId: string) {
  const units = await call<UnitItem[]>(request, phone, 'GET', `/centers/${centerId}/units/`)
  // Seulement les animaux étiquetés QR du seed : jamais les bovins de la démo RFID.
  return units.filter((u) => u.kind === 'animal' && u.label_code)
}

async function declare(request: APIRequestContext, phone: string, from: Center, to: Center, unitId: string) {
  return call<{ id: string; confirmation_code: string }>(request, phone, 'POST', '/movements/', {
    from_center_id: from.id, to_center_id: to.id, movement_type: 'sale',
    items: [{ unit_id: unitId, quantity_sent: 1 }],
  }, 201)
}

/** Rejouable : annule (sans rien effacer) les départs encore ouverts de l'Élevage B. */
async function cancelOpenDeparturesFromB(request: APIRequestContext) {
  const b = await center(request, PHONES.breeder2, 'Élevage B (simulé)')
  type Listed = { id: string; status: string; from_center: string; confirmations: { side: string }[] }
  const movements = await call<Listed[]>(request, PHONES.breeder2, 'GET', `/movements/?center_id=${b.id}`)
  // Seuls les départs jamais reçus s'annulent (une entrée au marché est déjà reçue).
  const open = movements.filter((m) => m.status === 'declared' && m.from_center === b.id
    && !m.confirmations.some((c) => c.side === 'receiver'))
  for (const m of open) {
    await call(request, PHONES.breeder2, 'POST', `/movements/${m.id}/cancel/`,
               { center_id: b.id, reason: 'Nettoyage du test E2E' })
  }
}

async function login(page: Page, phone: string) {
  await page.goto('/connexion')
  await page.getByLabel(/téléphone/i).fill(phone)
  await page.getByLabel(/mot de passe/i).fill(password)
  await page.getByRole('button', { name: /se connecter/i }).click()
  await page.waitForURL('/')
}

test.describe.serial('Plan de test : assistée, contestation, hors ligne, parcours de démo', () => {
  test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser les comptes de démonstration.')
  test.beforeAll(async ({ request }) => cancelOpenDeparturesFromB(request))

  test('2. confirmation assistée : l’agent mandaté reçoit pour l’Élevage B', async ({ page, request }) => {
    const c = await center(request, PHONES.breeder3, 'Élevage C (simulé)')
    const b = await center(request, PHONES.breeder2, 'Élevage B (simulé)')
    const atC = await animals(request, PHONES.breeder3, c.id)
    expect(atC.length, 'Il faut un animal à l’Élevage C').toBeGreaterThan(0)
    const { id, confirmation_code } = await declare(request, PHONES.breeder3, c, b, atC[0].id)

    await login(page, PHONES.agent)
    await page.goto('/mouvements/recevoir')
    await expect(page.getByRole('heading', { name: 'Confirmer la réception' })).toBeVisible()
    const select = page.getByLabel('Élevage destinataire')
    if (await select.count()) await select.selectOption({ label: 'Élevage B (simulé)' })
    await expect(page.getByText('Confirmation assistée')).toBeVisible()
    await page.getByLabel(/Référence complète du départ/i).fill(id)
    await page.getByLabel('Code de confirmation').fill(confirmation_code)
    await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
    await expect(page.getByText('L’élevage destinataire est maintenant associé aux animaux reçus.'))
      .toBeVisible({ timeout: 10_000 })

    const movement = await call<{ confirmations: { side: string; mode: string }[] }>(
      request, PHONES.breeder2, 'GET', `/movements/${id}/?center_id=${b.id}`)
    expect(movement.confirmations.find((c) => c.side === 'receiver')?.mode).toBe('assisted')
  })

  test('6. contester un mouvement reçu : l’animal ne bouge pas', async ({ page, request }) => {
    const b = await center(request, PHONES.breeder2, 'Élevage B (simulé)')
    const c = await center(request, PHONES.breeder3, 'Élevage C (simulé)')
    const atB = await animals(request, PHONES.breeder2, b.id)
    expect(atB.length, 'Il faut un animal à l’Élevage B').toBeGreaterThan(0)
    const { id, confirmation_code } = await declare(request, PHONES.breeder2, b, c, atB[0].id)
    await call(request, PHONES.breeder3, 'POST', `/movements/${id}/confirm/`,
               { center_id: c.id, code: confirmation_code })

    await login(page, PHONES.breeder2)
    await page.goto('/mouvements/historique')
    await expect(page.getByRole('heading', { name: 'Mes mouvements' })).toBeVisible()
    const select = page.getByLabel('Élevage', { exact: true })
    if (await select.count()) await select.selectOption({ label: 'Élevage B (simulé)' })
    const card = page.locator('li').filter({ hasText: 'Départ vers Élevage C (simulé)' })
      .filter({ hasText: 'Confirmé' }).first()
    await card.getByRole('button', { name: 'Contester' }).click()
    await card.getByRole('button', { name: 'Contester' }).click()
    await expect.poll(async () => (await call<{ status: string }>(
      request, PHONES.breeder2, 'GET', `/movements/${id}/?center_id=${b.id}`)).status,
    { timeout: 10_000 }).toBe('disputed')
    const stillAtC = await animals(request, PHONES.breeder3, c.id)
    expect(stillAtC.some((u) => u.id === atB[0].id)).toBeTruthy()
  })

  test('8. hors ligne puis retour du réseau : la déclaration part toute seule', async ({ page }) => {
    await login(page, PHONES.breeder2)
    await page.goto('/mouvements')
    // Attendre la fin du chargement avant de choisir B : sinon le choix est perdu et le
    // départ part de l'Élevage A (celui de l'Animal 1 réservé à la démo).
    const source = page.getByLabel('Élevage de départ')
    await expect(source).toBeVisible()
    await source.selectOption({ label: 'Élevage B (simulé)' })
    await expect(source).toHaveValue(/.+/)
    // Nouveau style : chaque animal est montré par son code d'étiquette et son espèce.
    const animal = page.locator('section[aria-labelledby="units-heading"] button')
      .filter({ hasText: /[2-9A-HJ-NP-Z]{9}/ }).filter({ hasText: /Animal/ }).first()
    await expect(animal).toBeVisible()
    await expect(page.locator('section[aria-labelledby="units-heading"]')).not.toContainText(DEMO_ANIMAL_CODE)
    await page.getByRole('button', { name: 'Vente' }).click()
    await page.context().setOffline(true)
    await animal.click()
    await page.getByRole('textbox', { name: 'Autre destination' }).fill('Acheteur de test (hors ligne)')
    await page.getByRole('button', { name: 'Déclarer' }).click()
    await expect(page.getByText('En attente d’envoi').first()).toBeVisible()

    await page.context().setOffline(false)
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await expect(page.getByText('Envoyé au serveur.')).toBeVisible({ timeout: 15_000 })
  })

  test('9. parcours de démo : signalement à A, validation, B et marché exposés, D écarté', async ({ page, request }) => {
    const a = await center(request, PHONES.breeder1, 'Élevage A (simulé)')
    const cow = (await animals(request, PHONES.breeder1, a.id)).find((u) => u.label_code === DEMO_ANIMAL_CODE)
    expect(cow, 'L’Animal 1 (KECTT2U8V) doit être à l’Élevage A').toBeTruthy()

    const reportId = crypto.randomUUID()
    await call(request, PHONES.breeder1, 'POST', '/health-reports/', {
      id: reportId, center_id: a.id, report_kind: 'suspicion', affected_count: 1, dead_count: 0,
      self_severity: 'high', occurred_at: new Date().toISOString(), symptom_codes: ['fever'],
      subjects: [{ unit_id: cow!.id, condition: 'sick' }],
    }, 201)
    await call(request, PHONES.vet, 'POST', `/health-reports/${reportId}/review/`, {
      id: crypto.randomUUID(), decision: 'validate_level3', disease_code: 'fmd', note: 'Test E2E',
    }, 201)

    type Exposure = { center: { name: string }; status: string; depth: number }
    const alerts = await call<{ id: string; level: number; focus_center: { id: string } | null; opened_at: string }[]>(
      request, PHONES.vet, 'GET', '/alerts/')
    const alert = alerts.filter((x) => x.focus_center?.id === a.id && x.level === 3)
      .sort((x, y) => y.opened_at.localeCompare(x.opened_at))[0]
    expect(alert, 'Une alerte validée (niveau 3) existe pour l’Élevage A').toBeTruthy()
    const detail = await call<{ exposures: Exposure[] }>(request, PHONES.vet, 'GET', `/alerts/${alert.id}/`)
    const byName = (name: string) => detail.exposures.find((e) => e.center.name === name)
    expect(byName('Élevage B (simulé)')?.status).toBe('exposed')
    expect(byName('Élevage B (simulé)')?.depth).toBe(1)
    expect(byName('Marché (simulé)')?.status).toBe('exposed')
    expect(byName('Marché (simulé)')?.depth).toBe(2)
    expect(byName('Élevage D (simulé)')?.status).toBe('excluded_negative')

    // Ce que voit le vétérinaire à l'écran.
    await login(page, PHONES.vet)
    await page.goto(`/alertes/${alert.id}`)
    await expect(page.getByText('Élevage B (simulé)').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Marché (simulé)').first()).toBeVisible()
    await expect(page.getByText('Élevage D (simulé)').first()).toBeVisible()
    await expect(page.getByText('Écarté').first()).toBeVisible()

    // RG-13 / RG-16 : l'éleveur B reçoit un message neutre, sans le nom de l'élevage d'origine.
    const notifications = await call<unknown[]>(request, PHONES.breeder2, 'GET', '/notifications/')
    const text = JSON.stringify(notifications)
    expect(text).toContain('exposure')
    expect(text).not.toContain('Élevage A')
  })
})
