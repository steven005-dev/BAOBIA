import { useEffect, useState } from 'react'
import { CircleCheck, PackageCheck, QrCode } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { erreurs, messages } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { identityApi } from '@/features/identity/api'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'
import { SyncStatusBanner } from '@/components/SyncStatusBanner'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function ConfirmMovementReceiptPage() {
  const navigate = useNavigate()
  const centersResource = useResource(identityApi.centers, 'centres-destinataires')
  const centers = centersResource.data ?? []
  const [centerId, setCenterId] = useState('')
  const center = centers.find((item) => item.id === centerId) ?? centers[0]
  const [movementId, setMovementId] = useState('')
  const [code, setCode] = useState('')
  const [operationId, setOperationId] = useState<string | null>(null)
  const [operationStatus, setOperationStatus] = useState<OperationStatus>('pending')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!operationId) return
    return subscribeOperation(operationId, (operation) => {
      if (operation) setOperationStatus(operation.status === 'sending' ? 'pending' : operation.status)
    })
  }, [operationId])

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (centers.length === 0) {
    return <EmptyState icon={PackageCheck} title={messages.aucunElevage} text={messages.aucunElevageAide} />
  }

  if (operationId) {
    return (
      <section className="flex flex-col gap-5 rounded-xl border-2 border-border bg-surface p-5 shadow-card">
        <SyncStatusBanner status={operationStatus} />
        {operationStatus === 'sent' ? (
          <Banner variant="success" title={messages.receptionEnregistree}>
            L’élevage destinataire est maintenant associé aux animaux reçus.
          </Banner>
        ) : (
          <p className="text-body text-muted-foreground">La réception sera confirmée après l’envoi au serveur.</p>
        )}
        <Button
          icon={PackageCheck}
          variant="secondary"
          fullWidth
          onClick={() => {
            setOperationId(null)
            setCode('')
            setMovementId('')
            setOperationStatus('pending')
          }}
        >
          Nouvelle réception
        </Button>
      </section>
    )
  }

  const send = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    if (!center || !UUID_PATTERN.test(movementId.trim()) || !/^\d{6}$/.test(code)) {
      setError(erreurs.saisie)
      return
    }

    const id = newUuid()
    setSaving(true)
    try {
      await submit({
        id,
        type: 'movement.confirm',
        path: `/movements/${movementId.trim()}/confirm/`,
        method: 'POST',
        body: { id, center_id: center.id, code, occurred_at: new Date().toISOString() },
      })
      setOperationId(id)
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : erreurs.reseau)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={send} className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">Confirmer la réception</h1>
      <Button type="button" icon={QrCode} variant="secondary" fullWidth onClick={() => navigate('/mouvements/partager')}>
        Partager mon élevage avec l’expéditeur
      </Button>
      {error && <Banner variant="error">{error}</Banner>}
      {centers.length > 1 ? (
        <Field label="Élevage destinataire" required>
          <Select
            value={center?.id ?? ''}
            onChange={(event) => setCenterId(event.target.value)}
            options={centers.map((item) => ({ value: item.id, label: item.name }))}
          />
        </Field>
      ) : (
        <p className="text-body font-bold text-foreground">Élevage destinataire · {center?.name}</p>
      )}
      <Field label="Référence complète du départ" help="Demandez la référence complète à l’éleveur expéditeur." required>
        <Input
          value={movementId}
          onChange={(event) => setMovementId(event.target.value)}
          autoCapitalize="none"
          spellCheck={false}
          required
        />
      </Field>
      <Field label="Code de confirmation" help="Entrez le code à six chiffres transmis par l’expéditeur." required>
        <Input
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
          required
        />
      </Field>
      <Button type="submit" icon={CircleCheck} fullWidth loading={saving} disabled={!center || code.length !== 6 || !movementId}>
        Confirmer
      </Button>
    </form>
  )
}
