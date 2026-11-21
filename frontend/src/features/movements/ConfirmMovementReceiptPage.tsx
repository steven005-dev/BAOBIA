import { useEffect, useState } from 'react'
import { CircleCheck, CircleX, ListChecks, PackageCheck, QrCode, UserCheck } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { NumberStepper } from '@/components/NumberStepper'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { erreurs, messages, mots } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { identityApi } from '@/features/identity/api'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'
import { SyncStatusBanner } from '@/components/SyncStatusBanner'

import { movementApi, REASONS, type Movement, type MovementItem } from './api'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

type Step = 'confirm' | 'count' | 'refuse'

export function ConfirmMovementReceiptPage() {
  const navigate = useNavigate()
  const centersResource = useResource(identityApi.centers, 'centres-destinataires')
  const centers = centersResource.data ?? []
  const [centerId, setCenterId] = useState('')
  const center = centers.find((item) => item.id === centerId) ?? centers[0]
  const [movementId, setMovementId] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<Step>('confirm')
  const [items, setItems] = useState<MovementItem[] | null>(null)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [reason, setReason] = useState<string>(REASONS.refuse[0])
  const [operationId, setOperationId] = useState<string | null>(null)
  const [operationKind, setOperationKind] = useState<'confirm' | 'refuse'>('confirm')
  const [operationStatus, setOperationStatus] = useState<OperationStatus>('pending')
  const [result, setResult] = useState<Movement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!operationId) return
    return subscribeOperation(operationId, (operation) => {
      if (!operation) return
      setOperationStatus(operation.status === 'sending' ? 'pending' : operation.status)
      if (operation.response) setResult(operation.response as Movement)
      if (operation.status === 'check') setError(operation.last_error ?? erreurs.saisie)
    })
  }, [operationId])

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (centers.length === 0) {
    return <EmptyState icon={PackageCheck} title={messages.aucunElevage} text={messages.aucunElevageAide} />
  }

  const reset = () => {
    setOperationId(null)
    setCode('')
    setMovementId('')
    setStep('confirm')
    setItems(null)
    setCounts({})
    setResult(null)
    setError(null)
    setOperationStatus('pending')
  }

  if (operationId) {
    const partial = result?.status === 'partial'
    return (
      <section className="flex flex-col gap-5 rounded-xl border-2 border-border bg-surface p-5 shadow-card">
        <SyncStatusBanner status={operationStatus} />
        {operationStatus === 'sent' && operationKind === 'refuse' && (
          <Banner variant="warning" title="Réception refusée.">
            Le départ est marqué contesté. Les animaux restent à l’élevage de départ.
          </Banner>
        )}
        {operationStatus === 'sent' && operationKind === 'confirm' && (
          <Banner variant={partial ? 'warning' : 'success'}
                  title={partial ? 'Réception enregistrée avec écart.' : messages.receptionEnregistree}>
            {partial
              ? 'L’écart est signalé aux deux élevages. Les animaux non reçus restent à l’élevage de départ.'
              : 'L’élevage destinataire est maintenant associé aux animaux reçus.'}
          </Banner>
        )}
        {operationStatus === 'check' && error && <Banner variant="error">{error}</Banner>}
        {operationStatus === 'pending' && (
          <p className="text-body text-muted-foreground">La réception sera confirmée après l’envoi au serveur.</p>
        )}
        <Button icon={PackageCheck} variant="secondary" fullWidth onClick={reset}>
          Nouvelle réception
        </Button>
      </section>
    )
  }

  const validInput = !!center && UUID_PATTERN.test(movementId.trim())

  const loadItems = async () => {
    setError(null)
    if (!validInput || !center) {
      setError(erreurs.saisie)
      return
    }
    try {
      const movement = await movementApi.detail(movementId.trim(), center.id)
      setItems(movement.items)
      setCounts(Object.fromEntries(movement.items.map((item) => [item.unit, item.quantity_sent])))
      setStep('count')
    } catch (loadError) {
      setError(loadError instanceof ApiError && loadError.kind === 'network'
        ? 'Connexion nécessaire pour compter les animaux. Réessayez avec du réseau.'
        : loadError instanceof ApiError ? loadError.message : erreurs.reseau)
    }
  }

  const send = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    const refusing = step === 'refuse'
    if (!validInput || !center || (!refusing && !/^\d{6}$/.test(code))) {
      setError(erreurs.saisie)
      return
    }

    const id = newUuid()
    const target = movementId.trim()
    const occurredAt = new Date().toISOString()
    setSaving(true)
    try {
      if (refusing) {
        await submit({
          id,
          type: 'movement.refuse',
          path: `/movements/${target}/refuse/`,
          method: 'POST',
          body: { id, center_id: center.id, reason, occurred_at: occurredAt },
        })
      } else {
        const itemsReceived = step === 'count' && items
          ? items.map((item) => ({ unit_id: item.unit, quantity_received: counts[item.unit] ?? 0 }))
          : []
        await submit({
          id,
          type: 'movement.confirm',
          path: `/movements/${target}/confirm/`,
          method: 'POST',
          body: { id, center_id: center.id, code, occurred_at: occurredAt, items_received: itemsReceived },
        })
      }
      setOperationKind(refusing ? 'refuse' : 'confirm')
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
      {center?.access === 'mandate' && (
        <Banner variant="info" title="Confirmation assistée">
          <span className="inline-flex items-center gap-2">
            <UserCheck aria-hidden className="size-icon-badge" />
            Vous saisissez pour {center.name}. Elle sera enregistrée comme assistée, pas comme directe.
          </span>
        </Banner>
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

      {step === 'refuse' ? (
        <>
          <Field label="Motif du refus" required>
            <Select
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              options={REASONS.refuse.map((item) => ({ value: item, label: item }))}
            />
          </Field>
          <p className="text-body text-muted-foreground">
            Le départ sera marqué contesté. BAOBIA ne tranche pas : les animaux restent à l’élevage de départ.
          </p>
          <Button type="submit" icon={CircleX} variant="danger" fullWidth loading={saving} disabled={!validInput}>
            {mots.refuser}
          </Button>
          <Button type="button" variant="ghost" onClick={() => setStep('confirm')}>{mots.retour}</Button>
        </>
      ) : (
        <>
          <Field label="Code de confirmation" help="Entrez le code à six chiffres transmis par l’expéditeur." required>
            <Input
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              required
            />
          </Field>
          {step === 'count' && items && (
            <section aria-labelledby="count-heading" className="flex flex-col gap-4">
              <h2 id="count-heading" className="text-subtitle font-bold text-foreground">Nombre reçu</h2>
              {items.map((item) => (
                <NumberStepper
                  key={item.unit}
                  label={`${item.unit_local_name ?? (item.unit_kind === 'lot' ? mots.lot : mots.animal)} · ${item.quantity_sent} parti(s)`}
                  value={counts[item.unit] ?? 0}
                  min={0}
                  max={item.quantity_sent}
                  onChange={(value) => setCounts((current) => ({ ...current, [item.unit]: value }))}
                />
              ))}
            </section>
          )}
          <Button type="submit" icon={CircleCheck} fullWidth loading={saving}
                  disabled={!center || code.length !== 6 || !movementId}>
            {mots.confirmer}
          </Button>
          {step === 'confirm' && (
            <Button type="button" icon={ListChecks} variant="secondary" fullWidth onClick={() => void loadItems()}
                    disabled={!validInput}>
              Il manque des animaux
            </Button>
          )}
          <Button type="button" icon={CircleX} variant="ghost" onClick={() => setStep('refuse')} disabled={!validInput}>
            Refuser la réception
          </Button>
        </>
      )}
    </form>
  )
}
