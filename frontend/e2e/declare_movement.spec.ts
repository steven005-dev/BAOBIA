import { test, expect } from '@playwright/test'

test.describe('Déclaration de mouvement (MV-01, TR-05)', () => {
  test('un destinataire partage son élevage et confirme un transfert entre deux comptes', async ({ page }) => {
    const password = process.env.SEED_DEMO_PASSWORD
    test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser le compte de démonstration.')

    // Le destinataire partage d'abord son élevage B avec l'expéditeur.
    await page.goto('/connexion')
    await page.getByLabel(/téléphone/i).fill('0000000002')
    await page.getByLabel(/mot de passe/i).fill(password!)
    await page.getByRole('button', { name: /se connecter/i }).click()
    await page.waitForURL('/')

    await page.goto('/mouvements/partager')
    await page.getByLabel('Élevage à partager').selectOption({ label: 'Élevage B (simulé)' })
    await page.getByRole('button', { name: 'Créer un code de partage' }).click()
    const destinationCode = await page.getByLabel('Code de partage').inputValue()
    expect(destinationCode).toBeTruthy()

    // Deux contextes distincts représentent les téléphones de l'expéditeur et du destinataire.
    const browser = page.context().browser()
    if (!browser) throw new Error('Navigateur Playwright indisponible.')
    const senderContext = await browser.newContext()
    const senderPage = await senderContext.newPage()
    await senderPage.goto('/connexion')
    await senderPage.getByLabel(/téléphone/i).fill('0000000001')
    await senderPage.getByLabel(/mot de passe/i).fill(password!)
    await senderPage.getByRole('button', { name: /se connecter/i }).click()
    await senderPage.waitForURL('/')

    const sourceUnitsResponse = senderPage.waitForResponse(
      (response) => response.url().includes('/units/') && response.request().method() === 'GET',
    )
    await senderPage.goto('/mouvements')
    const sourceUnits = (await (await sourceUnitsResponse).json()) as Array<{ id: string }>
    const sourceCenterSelect = senderPage.getByLabel('Élevage de départ')
    if (await sourceCenterSelect.count()) {
      await sourceCenterSelect.selectOption({ label: 'Élevage A (simulé)' })
    }
    await senderPage.locator('section[aria-labelledby="units-heading"] button').first().click()
    await senderPage.getByLabel('Code de partage du destinataire').fill(destinationCode)
    await senderPage.getByRole('button', { name: 'Vérifier le code' }).click()
    await expect(senderPage.getByRole('status').filter({ hasText: 'Élevage destinataire vérifié' })).toContainText('Élevage B (simulé)')
    await senderPage.getByRole('button', { name: 'Déclarer' }).click()

    await expect(senderPage.getByRole('heading', { name: 'Départ enregistré' })).toBeVisible()
    const movementId = await senderPage
      .locator('dd[aria-label="Identifiant complet du mouvement"]')
      .innerText()
    const codeBanner = senderPage
      .getByRole('status')
      .filter({ hasText: 'Code de confirmation à transmettre' })
    await expect(codeBanner).toBeVisible()
    const code = (await codeBanner.innerText()).match(/\b\d{6}\b/)?.[0]
    expect(code).toBeTruthy()

    // Le compte destinataire resté connecté sur son propre appareil confirme la réception.
    await page.goto('/mouvements/recevoir')
    await page.getByLabel('Élevage destinataire').selectOption({ label: 'Élevage B (simulé)' })
    await page.getByLabel(/Référence complète du départ/i).fill(movementId)
    await page.getByLabel('Code de confirmation').fill(code!)
    await page.getByRole('button', { name: 'Confirmer' }).click()

    await expect(page.getByText(/associé aux animaux reçus/i)).toBeVisible({ timeout: 10_000 })
    await page.goto(`/centres/animaux/${sourceUnits[0].id}`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('Élevage B (simulé)', { exact: true })).toBeVisible()
    await senderContext.close()
  })

  test('un éleveur connecté garde sa déclaration dans IndexedDB hors ligne', async ({ page }) => {
    const pageErrors: Error[] = []
    const consoleErrors: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error))
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text())
    })
    const password = process.env.SEED_DEMO_PASSWORD
    test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser le compte de démonstration.')

    await page.goto('/connexion')
    await page.getByLabel(/téléphone/i).fill('0000000001')
    await page.getByLabel(/mot de passe/i).fill(password!)
    await page.getByRole('button', { name: /se connecter/i }).click()
    await page.waitForURL('/')

    await page.goto('/mouvements')
    await expect(page.getByText('Illustration : données simulées.')).toBeVisible()
    // Les étiquettes du seed sont générées de façon déterministe, mais leur format peut évoluer.
    const animal = page.locator('section[aria-labelledby="units-heading"] button').first()
    await expect(animal).toBeVisible()

    // On coupe le réseau après le chargement des centres et des unités.
    await page.getByRole('button', { name: 'Vente' }).click()
    await page.context().setOffline(true)
    await animal.click()
    await page.getByRole('textbox', { name: 'Autre destination' }).fill('Marché à bétail de Bouaké')
    await page.getByRole('button', { name: 'Déclarer' }).click()

    await expect(page.getByRole('heading', { name: 'Départ enregistré' })).toBeVisible()
    await expect(
      page.getByRole('status').filter({ hasText: 'En attente d’envoi' }),
    ).toBeVisible()
    await expect(page.getByText('Marché à bétail de Bouaké')).toBeVisible()

    // TR-05 : l'opération est écrite dans Dexie avant toute synchronisation.
    const storedOperations = await page.evaluate(async () => {
      const database = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open('baobia_offline_db')
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
      const count = await new Promise<number>((resolve, reject) => {
        const request = database.transaction('operations', 'readonly').objectStore('operations').count()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
      database.close()
      return count
    })
    expect(storedOperations).toBe(1)
    expect(pageErrors.map((error) => error.message)).toEqual([])
    expect(consoleErrors).toEqual([])
  })
})
