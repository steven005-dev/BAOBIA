/**
 * Écrans du module mouvements ajoutés le 20-21/11 : réception avec écart (MV-06), refus
 * (MV-05/09), « Mes mouvements » avec annulation, et Marché (R2 : entrée, sortie hors système).
 *
 * Données : base de démo (`seed --demo` puis `seed_demo_traceability`). Les départs de test
 * sont créés par l'API, depuis l'Élevage B (Animaux 5, 6, 7), pour garder les bovins de
 * l'Élevage A pour la démonstration. Le scénario modifie la base de démo (données simulées).
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const password = process.env.SEED_DEMO_PASSWORD ?? ''
const api = process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000'
const PHONES = { breeder1: '0000000001', breeder2: '0000000002', breeder3: '0000000003' }

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

async function apiGet<T>(request: APIRequestContext, access: string, path: string) {
  const response = await request.get(`${api}/api${path}`, { headers: { Authorization: `Bearer ${access}` } })
  expect(response.ok()).toBeTruthy()
  return (await response.json()) as T
}

type UnitItem = { id: string; kind: string; local_name: string | null; label_code: string | null }

/** Animaux actuellement à l'Élevage B (le scénario ne dépend pas d'animaux précis). */
async function animalsAtB(request: APIRequestContext) {
  const access = await token(request, PHONES.breeder2)
  const centers = await apiGet<{ id: string; name: string }[]>(request, access, '/centers/')
  const b = centers.find((c) => c.name === 'Élevage B (simulé)')!
  const units = await apiGet<UnitItem[]>(request, access, `/centers/${b.id}/units/`)
  return { b, animals: units.filter((u) => u.kind === 'animal' && u.local_name) }
}

async function declareFromB(request: APIRequestContext, count: number) {
  const access = await token(request, PHONES.breeder2)
  const { b, animals } = await animalsAtB(request)
  expect(animals.length, `Il faut au moins ${count} animal(aux) à l'Élevage B`).toBeGreaterThanOrEqual(count)
  const chosen = animals.slice(0, count)
  const c = (await apiGet<{ id: string; name: string }[]>(request, await token(request, PHONES.breeder3), '/centers/'))
    .find((center) => center.name === 'Élevage C (simulé)')!
  const response = await request.post(`${api}/api/movements/`, {
    headers: { Authorization: `Bearer ${access}` },
    data: { from_center_id: b.id, to_center_id: c.id, movement_type: 'sale',
            items: chosen.map((u) => ({ unit_id: u.id, quantity_sent: 1 })) },
  })
  expect(response.status()).toBe(201)
  const body = (await response.json()) as { id: string; confirmation_code: string }
  return { movementId: body.id, code: body.confirmation_code, names: chosen.map((u) => u.local_name!) }
}

function escapeRegExp(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Rend le scénario rejouable : annule (sans rien effacer) les départs B -> C de test
 *  restés ouverts, qui verrouillent encore leurs animaux. */
async function cancelOpenTestDepartures(request: APIRequestContext) {
  const access = await token(request, PHONES.breeder2)
  const centers = await apiGet<{ id: string; name: string }[]>(request, access, '/centers/')
  const b = centers.find((c) => c.name === 'Élevage B (simulé)')!
  type Listed = { id: string; status: string; from_center: string; confirmations: { side: string }[] }
  const movements = await apiGet<Listed[]>(request, access, `/movements/?center_id=${b.id}`)
  for (const movement of movements) {
    // Tout départ de B jamais reçu (une entrée au marché est déjà reçue : elle reste).
    if (movement.status !== 'declared' || movement.from_center !== b.id
        || movement.confirmations.some((c) => c.side === 'receiver')) continue
    const response = await request.post(`${api}/api/movements/${movement.id}/cancel/`, {
      headers: { Authorization: `Bearer ${access}` },
      data: { center_id: b.id, reason: 'Nettoyage du test E2E' },
    })
    expect(response.ok()).toBeTruthy()
  }
}

async function login(page: Page, phone: string) {
  await page.goto('/connexion')
  await page.getByLabel(/téléphone/i).fill(phone)
  await page.getByLabel(/mot de passe/i).fill(password)
  await page.getByRole('button', { name: /se connecter/i }).click()
  await page.waitForURL('/')
}

async function openReceipt(page: Page, movementId: string) {
  await page.goto('/mouvements/recevoir')
  await expect(page.getByRole('heading', { name: 'Confirmer la réception' })).toBeVisible()
  const select = page.getByLabel('Élevage destinataire')
  if (await select.count()) await select.selectOption({ label: 'Élevage C (simulé)' })
  await page.getByLabel(/Référence complète du départ/i).fill(movementId)
}

test.describe.serial('Écrans mouvements : écart, refus, historique, marché', () => {
  test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser les comptes de démonstration.')
  test.beforeAll(async ({ request }) => cancelOpenTestDepartures(request))

  test('« Mes mouvements » affiche les départs de démonstration', async ({ page }) => {
    await login(page, PHONES.breeder1)
    await page.goto('/mouvements')
    await page.getByRole('button', { name: 'Mes mouvements' }).click()
    await expect(page.getByRole('heading', { name: 'Mes mouvements' })).toBeVisible()
    const select = page.getByLabel('Élevage', { exact: true })
    if (await select.count()) await select.selectOption({ label: 'Élevage A (simulé)' })
    await expect(page.getByText('Départ vers Élevage B (simulé)').first()).toBeVisible()
    await expect(page.getByText('Départ vers Élevage D (simulé)').first()).toBeVisible()
  })

  test('réception avec un animal manquant : écart enregistré', async ({ page, request }) => {
    const { movementId, code, names } = await declareFromB(request, 2)
    await login(page, PHONES.breeder3)
    await openReceipt(page, movementId)
    await page.getByLabel('Code de confirmation').fill(code)
    await page.getByRole('button', { name: 'Il manque des animaux' }).click()
    await expect(page.getByRole('heading', { name: 'Nombre reçu' })).toBeVisible()
    // Le second animal n'est pas arrivé : il reste à l'Élevage B.
    await page.getByLabel(new RegExp(escapeRegExp(names[1]))).fill('0')
    await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
    await expect(page.getByText('Réception enregistrée avec écart.')).toBeVisible({ timeout: 10_000 })
  })

  test('refus de réception : départ contesté', async ({ page, request }) => {
    const { movementId } = await declareFromB(request, 1)
    await login(page, PHONES.breeder3)
    await openReceipt(page, movementId)
    await page.getByRole('button', { name: 'Refuser la réception' }).click()
    await expect(page.getByLabel('Motif du refus')).toBeVisible()
    await page.getByRole('button', { name: 'Refuser', exact: true }).click()
    await expect(page.getByText('Réception refusée.')).toBeVisible({ timeout: 10_000 })
  })

  test('« Mes mouvements » : annuler un départ pas encore reçu', async ({ page, request }) => {
    await declareFromB(request, 1)
    await login(page, PHONES.breeder2)
    await page.goto('/mouvements/historique')
    await expect(page.getByRole('heading', { name: 'Mes mouvements' })).toBeVisible()
    const select = page.getByLabel('Élevage', { exact: true })
    if (await select.count()) await select.selectOption({ label: 'Élevage B (simulé)' })
    const card = page.locator('li').filter({ hasText: 'Probable : en attente de l’autre partie' }).first()
    await card.getByRole('button', { name: 'Annuler le départ' }).click()
    await card.getByRole('button', { name: 'Annuler le départ' }).click()
    await expect(page.getByText('Annulé').first()).toBeVisible({ timeout: 10_000 })
  })

  test('marché : entrée sans code puis sortie vers un acheteur non inscrit', async ({ page, request }) => {
    await cancelOpenTestDepartures(request)  // libère l'animal du test d'annulation s'il a échoué
    const labelled = (await animalsAtB(request)).animals.find((u) => u.label_code)
    expect(labelled, 'Il faut un animal étiqueté à l’Élevage B').toBeTruthy()
    const labelCode = labelled!.label_code!
    await login(page, PHONES.breeder3)
    await page.goto('/mouvements')
    await page.getByRole('button', { name: 'Marché : entrées et sorties' }).click()
    await expect(page.getByRole('heading', { name: 'Marché', exact: true })).toBeVisible()

    // Entrée (choisie par défaut) : chaque scan part aussitôt, la ligne passe au vert.
    await page.getByLabel('Numéro de boucle ou code').fill(labelCode)
    await page.getByRole('button', { name: 'Ajouter' }).click()
    await expect(page.getByRole('heading', { name: '1 animal entré' })).toBeVisible({ timeout: 10_000 })

    // Sortie vers un acheteur non inscrit : l'animal sort du système.
    await page.getByRole('radio', { name: /Sortie/ }).click()
    await page.getByLabel('Sinon, acheteur non inscrit').fill('Acheteur de Bouaké (test)')
    await page.getByLabel('Numéro de boucle ou code').fill(labelCode)
    await page.getByRole('button', { name: 'Ajouter' }).click()
    await expect(page.getByRole('heading', { name: '1 animal sorti' })).toBeVisible({ timeout: 10_000 })
  })
})
