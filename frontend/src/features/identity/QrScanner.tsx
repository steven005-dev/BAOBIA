/**
 * Lecture d'un QR code par la caméra arrière, avec l'API BarcodeDetector du navigateur
 * (Chrome et navigateurs Android récents) : aucune bibliothèque ajoutée.
 * Navigateur sans cette API ou caméra refusée : on le dit, et la saisie du code reste
 * possible à côté (charte : le code court se dicte et se tape).
 *
 * Exemple :
 *   <QrScanner onCode={(code) => chercher(code)} />
 */

import { ScanQrCode, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { messages, mots } from '@/lib/vocabulaire'

interface DetectedBarcode {
  rawValue: string
}
interface BarcodeDetectorLike {
  detect(source: HTMLVideoElement): Promise<DetectedBarcode[]>
}
type BarcodeDetectorCtor = new (options: { formats: string[] }) => BarcodeDetectorLike

function detectorClass(): BarcodeDetectorCtor | null {
  const ctor = (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector
  const hasCamera = typeof navigator.mediaDevices?.getUserMedia === 'function'
  return ctor && hasCamera ? ctor : null
}

export function QrScanner({ onCode }: { onCode: (code: string) => void }) {
  const [open, setOpen] = useState(false)
  const [failed, setFailed] = useState(() => detectorClass() === null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const onCodeRef = useRef(onCode)
  useEffect(() => {
    onCodeRef.current = onCode
  })

  useEffect(() => {
    if (!open) return
    const Detector = detectorClass()
    if (!Detector) return
    let stream: MediaStream | null = null
    let timer: number | undefined
    let stopped = false
    const detector = new Detector({ formats: ['qr_code'] })

    const scan = async () => {
      const video = videoRef.current
      if (stopped || !video) return
      try {
        if (video.readyState >= 2) {
          const found = await detector.detect(video)
          if (found[0]?.rawValue && !stopped) {
            stopped = true
            setOpen(false)
            onCodeRef.current(found[0].rawValue)
            return
          }
        }
      } catch {
        // Image illisible : on réessaie au tour suivant.
      }
      timer = window.setTimeout(scan, 250)
    }

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      .then((media) => {
        stream = media
        if (stopped || !videoRef.current) return
        videoRef.current.srcObject = media
        void videoRef.current.play().catch(() => {})
        void scan()
      })
      .catch(() => {
        setFailed(true)
        setOpen(false)
      })

    return () => {
      stopped = true
      window.clearTimeout(timer)
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [open])

  if (failed) return <Banner variant="info">{messages.cameraIndisponible}</Banner>

  if (!open) {
    return (
      <Button icon={ScanQrCode} onClick={() => setOpen(true)}>
        {mots.scanner}
      </Button>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-body text-foreground">{messages.visezEtiquette}</p>
      <video
        ref={videoRef}
        className="aspect-square w-full rounded-lg bg-foreground object-cover"
        muted
        playsInline
        aria-label={messages.visezEtiquette}
      />
      <Button variant="secondary" icon={X} onClick={() => setOpen(false)}>
        {mots.fermer}
      </Button>
    </div>
  )
}
