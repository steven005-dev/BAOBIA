/**
 * Scénario de démo du guide de réalisation des ajouts (21/11), avec les données de
 * `manage.py seed_demo_rfid` (à lancer sur une base neuve, le jour même) :
 * 1. boucle officielle saisie sur la fiche d'un animal ;
 * 2. marché, Entrée : Bovin D déclaré disparu (avertissement neutre), numéro inconnu ;
 * 3. bilan du jour ;
 * 4. parcours du Bovin C : transfert confirmé des deux côtés, badge « Sûr ».
 * Modifie la base de démo (données simulées).
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const password = process.env.SEED_DEMO_PASSWORD ?? ''
const api = process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000'

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

async function unitAt(request: APIRequestContext, phone: string, centerName: string,
                      match: (unit: { local_name: string | null; label_code: string | null }) => boolean) {
  const headers = { Authorization: `Bearer ${await token(request, phone)}` }
  const centers = (await (await request.get(`${api}/api/centers/`, { headers })).json()) as
    { id: string; name: string }[]
  const center = centers.find((c) => c.name === centerName)!
  const units = (await (await request.get(`${api}/api/centers/${center.id}/units/`, { headers })).json()) as
    { id: string; local_name: string | null; label_code: string | null }[]
  const unit = units.find(match)
  expect(unit, `Animal attendu à ${centerName}`).toBeTruthy()
  return unit!
}

async function login(page: Page, phone: string) {
  await page.goto('/connexion')
  await page.getByLabel(/téléphone/i).fill(phone)
  await page.getByLabel(/mot de passe/i).fill(password)
  await page.getByRole('button', { name: /se connecter/i }).click()
  await page.waitForURL('/')
}

test.describe.serial('Boucle RFID, marché, bilan et parcours (guide des ajouts)', () => {
  test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser les comptes de démonstration.')

  test('1. saisir le numéro de la boucle officielle sur la fiche', async ({ page, request }) => {
    const cow = await unitAt(request, '0000000001', 'Élevage A (simulé)', (u) => u.label_code === '82MRXN5SY')
    await login(page, '0000000001')
    await page.goto(`/centres/animaux/${cow.id}`)
    await expect(page.getByRole('heading', { name: 'Boucle officielle' })).toBeVisible({ timeout: 10_000 })
    const already = page.getByText('384 000 000 000 150')
    if (!(await already.isVisible())) {
      await page.getByRole('button', { name: 'Ajouter le numéro de la boucle officielle' }).click()
      await page.getByLabel('Numéro de la boucle').fill('384000000000150')
      await expect(page.getByText('15 / 15 chiffres')).toBeVisible()
      await page.getByRole('button', { name: 'Enregistrer la boucle' }).click()
    }
    await expect(page.getByText('384 000 000 000 150')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Numéro saisi à la main/)).toBeVisible()
  })

  test('2. marché : animal déclaré disparu et numéro inconnu, puis bilan du jour', async ({ page }) => {
    await login(page, '0000000003')
    await page.goto('/mouvements/marche')
    await expect(page.getByRole('heading', { name: 'Marché', exact: true })).toBeVisible()

    await page.getByLabel('Numéro de boucle ou code').fill('384 000 000 000 104')
    await page.getByRole('button', { name: 'Ajouter' }).click()
    const warning = page.locator('section[aria-labelledby="scanned-heading"] li').first()
    await expect(warning).toContainText("Cet animal fait l'objet d'une déclaration",
                                        { timeout: 10_000 })
    await expect(warning).not.toContainText(/vol|Élevage B/)
    await warning.getByRole('button', { name: 'J’ai compris' }).click()

    await page.getByLabel('Numéro de boucle ou code').fill('384000000000999')
    await page.getByRole('button', { name: 'Ajouter' }).click()
    await expect(page.getByText('Animal inconnu')).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: 'Bilan du jour' }).click()
    await expect(page.getByRole('heading', { name: 'Bilan du jour' })).toBeVisible()
    await expect(page.getByText('Entrés', { exact: true })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('region', { name: 'Zones d’origine (entrées)' })).toContainText('Zone Nord')
  })

  test('4. parcours du Bovin C : transfert confirmé, badge « Sûr »', async ({ page, request }) => {
    const cow = await unitAt(request, '0000000002', 'Élevage B (simulé)', (u) => u.local_name === 'Bovin C (simulé)')
    await login(page, '0000000002')
    await page.goto(`/centres/animaux/${cow.id}`)
    await expect(page.getByRole('heading', { name: 'Parcours' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Sûr', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('384 000 000 000 103')).toBeVisible()
  })
})
