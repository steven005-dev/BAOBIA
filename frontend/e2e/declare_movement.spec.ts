import { test, expect } from '@playwright/test'

test.describe('Écran Déclarer un départ (MV-01, TR-05)', () => {
  test('un éleveur peut sélectionner un animal, saisir la destination et enregistrer hors ligne', async ({
    page,
  }) => {
    // 1. Accès à la page
    await page.goto('/')

    // 2. Vérification des éléments de base (charte BAOBIA)
    await expect(page.getByRole('heading', { name: 'BAOBIA' })).toBeVisible()
    await expect(page.getByText('Données simulées')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Déclarer un départ' })).toBeVisible()

    // 3. Bouton principal visible avec mot et icône
    const submitBtn = page.getByRole('button', { name: 'Transférer' })
    await expect(submitBtn).toBeVisible()

    // 4. Sélection d'un animal (ex: Bovin #4892)
    const animalOption = page.getByRole('button', { name: /Bovin #4892/ })
    await animalOption.click()
    await expect(page.getByText('1 sélectionné(s)')).toBeVisible()

    // 5. Saisie du destinataire
    const destInput = page.getByLabel('Destination / Élevage destinataire *')
    await destInput.fill('Marché à bétail de Bouaké')

    // 6. Clic sur Transférer
    await submitBtn.click()

    // 7. Vérification de l'enregistrement hors ligne immédiat
    await expect(page.getByRole('heading', { name: 'Transfert enregistré' })).toBeVisible()
    await expect(
      page.getByText('Votre déclaration est enregistrée en sécurité sur ce téléphone')
    ).toBeVisible()

    // 8. Indicateur d'état : doit afficher 'En attente' (jamais 'Envoyé' sans serveur)
    await expect(page.getByRole('status')).toContainText("En attente d'envoi")
  })
})
