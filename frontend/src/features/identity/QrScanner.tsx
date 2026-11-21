/**
 * Lecture d'un QR code par la caméra arrière.
 * - Décodeur natif du navigateur (BarcodeDetector) quand il existe : Chrome Android, Mac.
 * - Sinon, bibliothèque de repli jsQR, chargée seulement à l'ouverture de la caméra :
 *   Chrome et Edge sur Windows, Safari sur iPhone, Firefox (guide développeur, « Scan QR »).
 * Sans caméra, caméra refusée ou adresse non sécurisée (http) : on dit pourquoi, et la
 * saisie du code reste possible à côté (charte : le code court se dicte et se tape).
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
type Decode = (video: HTMLVideoElement) => Promise<string | null>

function nativeDetector(): BarcodeDetectorCtor | null {
  return (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector ?? null
}

/** Pourquoi la caméra ne peut pas s'ouvrir du tout ; null si elle peut s'ouvrir. */
function cameraBlocker(): string | null {
  if (typeof navigator.mediaDevices?.getUserMedia === 'function') return null
  return window.isSecureContext ? messages.cameraIndisponible : messages.cameraHttps
}

/** Décodeur natif si présent, sinon jsQR sur une image de la vidéo. */
async function makeDecoder(): Promise<Decode> {
  const Native = nativeDetector()
  if (Native) {
    const detector = new Native({ formats: ['qr_code'] })
    return async (video) => (await detector.detect(video))[0]?.rawValue ?? null
  }
  const { default: jsQR } = await import('jsqr')
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d', { willReadFrequently: true })
  return async (video) => {
    if (!context || !video.videoWidth) return null
    // Une image réduite suffit pour un QR et reste rapide sur un téléphone modeste.
    const scale = Math.min(1, 640 / video.videoWidth)
    canvas.width = Math.round(video.videoWidth * scale)
    canvas.height = Math.round(video.videoHeight * scale)
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    const image = context.getImageData(0, 0, canvas.width, canvas.height)
    return jsQR(image.data, image.width, image.height, { inversionAttempts: 'dontInvert' })?.data ?? null
  }
}

function cameraError(error: unknown): string {
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError') return messages.cameraRefusee
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return messages.cameraAbsente
  return messages.cameraIndisponible
}

export function QrScanner({ onCode }: { onCode: (code: string) => void }) {
  const [open, setOpen] = useState(false)
  const [problem, setProblem] = useState<string | null>(() => cameraBlocker())
  const videoRef = useRef<HTMLVideoElement>(null)
  const onCodeRef = useRef(onCode)
  useEffect(() => {
    onCodeRef.current = onCode
  })

  useEffect(() => {
    if (!open) return
    let stream: MediaStream | null = null
    let timer: number | undefined
    let stopped = false

    const start = async () => {
      try {
        const [media, decode] = await Promise.all([
          navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false }),
          makeDecoder(),
        ])
        stream = media
        const video = videoRef.current
        if (stopped || !video) return
        video.srcObject = media
        await video.play().catch(() => {})

        const scan = async () => {
          if (stopped || !videoRef.current) return
          try {
            if (videoRef.current.readyState >= 2) {
              const value = await decode(videoRef.current)
              if (value && !stopped) {
                stopped = true
                setOpen(false)
                onCodeRef.current(value)
                return
              }
            }
          } catch {
            // Image illisible : on réessaie au tour suivant.
          }
          timer = window.setTimeout(scan, 250)
        }
        void scan()
      } catch (error) {
        if (stopped) return
        setProblem(cameraError(error))
        setOpen(false)
      }
    }
    void start()

    return () => {
      stopped = true
      window.clearTimeout(timer)
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [open])

  if (!open) {
    return (
      <div className="flex flex-col gap-3">
        {problem && <Banner variant="info">{problem}</Banner>}
        {/* Après un refus ou une erreur, on peut réessayer ; pas si la caméra est impossible
            (adresse http, navigateur sans accès caméra). */}
        {cameraBlocker() === null && (
          <Button icon={ScanQrCode} onClick={() => { setProblem(null); setOpen(true) }}>
            {mots.scanner}
          </Button>
        )}
      </div>
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
