import { useState } from 'react'
import { ArrowLeft, Copy, QrCode, Share2 } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { erreurs } from '@/lib/vocabulaire'

import { identityApi } from '@/features/identity/api'
import { useResource } from '@/features/identity/useResource'

import { movementApi, type DestinationShareCode } from './api'

export function ShareDestinationCodePage() {
  const navigate = useNavigate()
  const centersResource = useResource(identityApi.centers, 'centres-a-partager')
  const centers = centersResource.data ?? []
  const [centerId, setCenterId] = useState('')
  const center = centers.find((item) => item.id === centerId) ?? centers[0]
  const [share, setShare] = useState<DestinationShareCode | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (centers.length === 0) {
    return <Banner variant="warning">Aucun élevage auquel vous avez accès ne peut être partagé.</Banner>
  }

  const createCode = async () => {
    if (!center) return
    setError(null)
    setCopied(false)
    setLoading(true)
    try {
      setShare(await movementApi.shareDestinationCode(center.id))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : erreurs.serveur)
    } finally {
      setLoading(false)
    }
  }

  const copyCode = async () => {
    if (!share) return
    try {
      await navigator.clipboard.writeText(share.code)
      setCopied(true)
    } catch {
      setError('Impossible de copier le code. Vous pouvez le sélectionner et le copier manuellement.')
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate('/mouvements/recevoir')} className="self-start">
        Retour
      </Button>
      <div className="flex items-center gap-3">
        <Share2 aria-hidden className="size-icon text-primary" />
        <h1 className="text-title font-bold text-foreground">Partager mon élevage</h1>
      </div>
      <p className="text-body text-muted-foreground">
        Le destinataire peut scanner ce QR ou saisir le code pour choisir cet élevage comme destination.
        Le code expire après 30 jours.
      </p>
      {error && <Banner variant="error">{error}</Banner>}
      {centers.length > 1 ? (
        <Field label="Élevage à partager" required>
          <Select
            value={center?.id ?? ''}
            onChange={(event) => {
              setCenterId(event.target.value)
              setShare(null)
            }}
            options={centers.map((item) => ({ value: item.id, label: item.name }))}
          />
        </Field>
      ) : (
        <p className="rounded-md border-2 border-border bg-surface p-4 text-body font-bold text-foreground">
          {center?.name}
        </p>
      )}
      <Button icon={QrCode} fullWidth loading={loading} disabled={!center} onClick={() => void createCode()}>
        Créer un code de partage
      </Button>
      {share && (
        <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-border bg-surface p-5 text-center">
          <QRCodeSVG
            value={`BAOBIA-CENTER:${share.code}`}
            size={220}
            level="M"
            title={`QR de partage de ${center?.name ?? 'l’élevage'}`}
            className="max-w-full"
          />
          <Field label="Code de partage" help={`Valable ${share.expires_in_days} jours.`}>
            <textarea
              aria-label="Code de partage"
              readOnly
              value={share.code}
              rows={3}
              className="w-full resize-y rounded-md border-2 border-input bg-background p-3 font-mono text-caption text-foreground"
              onFocus={(event) => event.currentTarget.select()}
            />
          </Field>
          <Button icon={Copy} variant="secondary" fullWidth onClick={() => void copyCode()}>
            {copied ? 'Code copié' : 'Copier le code'}
          </Button>
          <p className="text-small text-muted-foreground">
            Transmettez ce code uniquement à la personne qui doit déclarer un transfert vers votre élevage.
          </p>
        </div>
      )}
    </section>
  )
}
