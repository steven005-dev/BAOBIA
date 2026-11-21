/**
 * Scan d'une vraie étiquette par la caméra, sur un navigateur SANS décodeur natif
 * (Chromium de Playwright sous Windows, comme Chrome Windows ou Safari iPhone) :
 * le décodeur de repli jsQR doit lire le QR.
 *
 * Une fausse caméra (vidéo Y4M générée ici) filme le QR d'une étiquette (Animal 7, chèvre de la
 * base de démo), généré comme sur l'étiquette imprimée (qrcode, correction « Q », marge 2).
 * Sur l'écran Marché, chaque scan part aussitôt : le test enregistre donc une Entrée
 * (données simulées). Rejoué, la ligne apparaît quand même (« Déjà scanné » ou refus).
 */
import { writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { expect, test } from '@playwright/test'
import QRCode from 'qrcode'

const password = process.env.SEED_DEMO_PASSWORD ?? ''
const api = process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000'
// Étiquette d'un animal de l'Élevage B dans la base de démo (voir seed.py, codes à graine fixe).
// La chèvre de l'Élevage B (Animal 7) : son passage n'a aucun effet sur l'alerte bovine de la démo.
const LABEL_CODE = process.env.E2E_SCAN_CODE ?? 'QGKQU8G4S'

/** Vidéo Y4M (niveaux de gris) qui montre le QR au centre, image fixe répétée. */
function writeQrVideo(code: string): string {
  const { modules } = QRCode.create(code, { errorCorrectionLevel: 'Q' })
  const size = 480
  const margin = 2
  const scale = Math.floor(400 / (modules.size + 2 * margin))
  const offset = Math.floor((size - scale * (modules.size + 2 * margin)) / 2) + margin * scale
  const luma = Buffer.alloc(size * size, 255)
  for (let row = 0; row < modules.size; row++) {
    for (let col = 0; col < modules.size; col++) {
      if (!modules.get(row, col)) continue
      for (let y = 0; y < scale; y++) {
        const start = (offset + row * scale + y) * size + offset + col * scale
        luma.fill(0, start, start + scale)
      }
    }
  }
  const chroma = Buffer.alloc((size / 2) * (size / 2), 128)
  const frame = Buffer.concat([Buffer.from('FRAME\n'), luma, chroma, chroma])
  const header = Buffer.from(`YUV4MPEG2 W${size} H${size} F10:1 Ip A1:1 C420jpeg\n`)
  const path = join(tmpdir(), `baobia-qr-${code}.y4m`)
  writeFileSync(path, Buffer.concat([header, ...Array(10).fill(frame)]))
  return path
}

const video = writeQrVideo(LABEL_CODE)

test.use({
  permissions: ['camera'],
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-video-capture=${video}`,
    ],
  },
})

test('scanner une étiquette avec la caméra, sans décodeur natif (repli jsQR)', async ({ page }) => {
  test.skip(!password, 'Définir SEED_DEMO_PASSWORD pour utiliser les comptes de démonstration.')
  expect(api).toBeTruthy()

  await page.goto('/connexion')
  await page.getByLabel(/téléphone/i).fill('0000000003')
  await page.getByLabel(/mot de passe/i).fill(password)
  await page.getByRole('button', { name: /se connecter/i }).click()
  await page.waitForURL('/')

  // Le test vise bien le cas sans décodeur natif.
  expect(await page.evaluate(() => 'BarcodeDetector' in window)).toBe(false)

  await page.goto('/mouvements/marche')
  await expect(page.getByRole('heading', { name: 'Marché', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Scanner' }).click()
  // Le code lu par la caméra apparaît dans la liste des scans (quel qu'en soit le résultat).
  await expect(page.locator('section[aria-labelledby="scanned-heading"] li').first())
    .toContainText(LABEL_CODE, { timeout: 15_000 })
})
