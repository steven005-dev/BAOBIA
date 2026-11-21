/**
 * Scan d'une vraie étiquette par la caméra, sur un navigateur SANS décodeur natif
 * (Chromium de Playwright sous Windows, comme Chrome Windows ou Safari iPhone) :
 * le décodeur de repli jsQR doit lire le QR.
 *
 * Une fausse caméra (vidéo Y4M générée ici) filme le QR d'une étiquette de l'Élevage B,
 * généré comme sur l'étiquette imprimée (qrcode, correction « Q », marge 2).
 * Le test s'arrête à la liste des animaux scannés : il n'écrit rien en base.
 */
import { writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { expect, test } from '@playwright/test'
import QRCode from 'qrcode'

const password = process.env.SEED_DEMO_PASSWORD ?? ''
const api = process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000'
// Étiquette d'un animal de l'Élevage B dans la base de démo (voir seed.py, codes à graine fixe).
const LABEL_CODE = process.env.E2E_SCAN_CODE ?? 'MYLHHLPGV'

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
  await page.getByRole('button', { name: /Entrée/ }).click()
  await page.getByRole('button', { name: 'Scanner' }).click()
  await expect(page.getByRole('heading', { name: '1 animal scanné' })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(LABEL_CODE)).toBeVisible()
})
