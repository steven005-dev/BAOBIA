/**
 * Étiquette à imprimer et à poser sur l'animal : QR code + code lisible + espèce.
 * Le QR ne contient QUE le code (règle : aucune donnée personnelle ni sanitaire).
 * Le QR est dessiné sur le téléphone (bibliothèque qrcode) : marche aussi hors ligne.
 * À l'impression, seule cette étiquette sort (classe print-label, voir globals.css).
 *
 * Exemple : <LabelToPrint code="ACNXQ6Z4N" species="Bovin" />
 */

import { Printer } from 'lucide-react'
import QRCode from 'qrcode'
import { useEffect, useState } from 'react'

import { Button } from '@/components/Button'
import { formatShortCode } from '@/lib/shortCode'
import { APP_NAME, mots } from '@/lib/vocabulaire'

export function LabelToPrint({ code, species }: { code: string; species: string }) {
  const [svg, setSvg] = useState<{ code: string; src: string } | null>(null)

  useEffect(() => {
    let alive = true
    // Correction d'erreur « Q » (25 %) : le QR reste lisible même un peu abîmé ou sale.
    QRCode.toString(code, { type: 'svg', errorCorrectionLevel: 'Q', margin: 2 }).then(
      (markup) => alive && setSvg({ code, src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}` }),
      () => alive && setSvg(null),
    )
    return () => {
      alive = false
    }
  }, [code])

  const readable = formatShortCode(code)
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="print-label flex w-full max-w-xs flex-col items-center gap-2 rounded-lg border-2 border-foreground bg-card p-4">
        <p className="text-caption font-bold text-foreground">{APP_NAME}</p>
        {svg?.code === code && <img src={svg.src} alt={readable} className="aspect-square w-full" />}
        <p className="text-subtitle font-bold tracking-widest text-foreground">{readable}</p>
        <p className="text-caption text-foreground">{species}</p>
      </div>
      <Button variant="secondary" icon={Printer} onClick={() => window.print()}>
        {mots.imprimer}
      </Button>
    </div>
  )
}
