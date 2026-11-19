/**
 * Mes mouvements : départs et arrivées d'un élevage, avec leur état (MV-05, MV-08),
 * le mode de confirmation (MV-04), les écarts (MV-06) et les actions Annuler / Contester
 * (MV-05, MV-09). Les actions passent par la file hors ligne ; la liste est lue en ligne.
 */

import { useState } from 'react'
import { Ban, Clock, Flag, History, TriangleAlert, UserCheck } from 'lucide-react'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { SyncStatusBanner } from '@/components/SyncStatusBanner'
import { ApiError } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { erreurs, messages } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { identityApi } from '@/features/identity/api'
import { useResource } from '@/features/identity/useResource'

import { MOVEMENT_STATUS_LABELS, REASONS, movementApi, type Movement } from './api'

type Action = 'cancel' | 'contest'

const ACTION_LABELS: Record<Action, string> = { cancel: 'Annuler le départ', contest: 'Contester' }

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function MovementCard({ movement, centerId, onDone }: {
  movement: Movement
  centerId: string
  onDone: (status: OperationStatus) => void
}) {
  const outgoing = movement.from_center === centerId
  const action: Action | null =
    outgoing && movement.status === 'declared' ? 'cancel'
      : ['confirmed', 'partial'].includes(movement.status) ? 'contest' : null
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<string>(action ? REASONS[action][0] : '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const other = outgoing ? (movement.to_center_name ?? movement.to_party_note ?? '—') : movement.from_center_name
  const assisted = movement.confirmations.filter((c) => c.mode === 'assisted')
  const count = movement.items.reduce((total, item) => total + item.quantity_sent, 0)

  const act = async () => {
    if (!action) return
    const id = newUuid()
    setSaving(true)
    setError(null)
    try {
      const result = await submit({
        id,
        type: `movement.${action}`,
        path: `/movements/${movement.id}/${action}/`,
        method: 'POST',
        body: { center_id: centerId, reason, occurred_at: new Date().toISOString() },
      })
      setOpen(false)
      onDone(result.status)
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : erreurs.reseau)
    } finally {
      setSaving(false)
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-xl border-2 border-border bg-surface p-4 shadow-card">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-body font-bold text-foreground">
          {outgoing ? 'Départ vers' : 'Arrivée de'} {other}
        </p>
        <span className="rounded-full border-2 border-border px-3 text-caption font-bold text-foreground">
          {MOVEMENT_STATUS_LABELS[movement.status]}
        </span>
      </div>
      <p className="text-small text-muted-foreground">
        {formatDate(movement.occurred_at)} · {count} {count > 1 ? 'animaux' : 'animal'}
      </p>
      {assisted.map((c) => (
        <p key={c.id} className="inline-flex items-center gap-2 text-small text-foreground">
          <UserCheck aria-hidden className="size-icon-badge" />
          {c.side === 'sender' ? 'Départ saisi' : 'Réception saisie'} par {c.entered_by_name} (assistée)
        </p>
      ))}
      {movement.discrepancies.map((d) => (
        <p key={d.id} className="inline-flex items-center gap-2 text-small text-foreground">
          <TriangleAlert aria-hidden className="size-icon-badge" />
          Écart : {d.quantity_found ?? 0} reçu(s) sur {d.quantity_expected ?? 0}
          {d.unit_local_name ? ` · ${d.unit_local_name}` : ''}
        </p>
      ))}
      {movement.clock_suspect && (
        <p className="inline-flex items-center gap-2 text-small text-foreground">
          <Clock aria-hidden className="size-icon-badge" />
          Date du téléphone dans le futur : à vérifier
        </p>
      )}
      {error && <Banner variant="error">{error}</Banner>}
      {action && !open && (
        <Button variant="ghost" icon={action === 'cancel' ? Ban : Flag} onClick={() => setOpen(true)}>
          {ACTION_LABELS[action]}
        </Button>
      )}
      {action && open && (
        <div className="flex flex-col gap-3">
          <Field label="Motif" required>
            <Select
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              options={REASONS[action].map((item) => ({ value: item, label: item }))}
            />
          </Field>
          {action === 'contest' && (
            <p className="text-small text-muted-foreground">
              Toutes les versions sont gardées. BAOBIA ne tranche pas le désaccord.
            </p>
          )}
          <Button variant="danger" icon={action === 'cancel' ? Ban : Flag} loading={saving} fullWidth
                  onClick={() => void act()}>
            {ACTION_LABELS[action]}
          </Button>
          <Button variant="ghost" onClick={() => setOpen(false)}>Retour</Button>
        </div>
      )}
    </li>
  )
}

export function MovementHistoryPage() {
  const centersResource = useResource(identityApi.centers, 'centres-historique')
  const centers = centersResource.data ?? []
  const [centerId, setCenterId] = useState('')
  const center = centers.find((item) => item.id === centerId) ?? centers[0]
  const [reloadKey, setReloadKey] = useState(0)
  const [lastStatus, setLastStatus] = useState<OperationStatus | null>(null)
  const movementsResource = useResource(
    () => (center ? movementApi.list(center.id) : Promise.resolve([] as Movement[])),
    `mouvements-${center?.id ?? 'aucun'}-${reloadKey}`,
  )

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (!center) {
    return <EmptyState icon={History} title={messages.aucunElevage} text={messages.aucunElevageAide} />
  }
  const movements = movementsResource.data ?? []

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">Mes mouvements</h1>
      {centers.length > 1 && (
        <Field label="Élevage">
          <Select
            value={center.id}
            onChange={(event) => setCenterId(event.target.value)}
            options={centers.map((item) => ({ value: item.id, label: item.name }))}
          />
        </Field>
      )}
      {lastStatus && <SyncStatusBanner status={lastStatus} />}
      {movementsResource.loading && <Loader />}
      {movementsResource.error && (
        <Banner variant="error">
          {movementsResource.error instanceof ApiError && movementsResource.error.kind === 'network'
            ? 'Connexion nécessaire pour afficher la liste.'
            : movementsResource.error.message}
        </Banner>
      )}
      {!movementsResource.loading && !movementsResource.error && movements.length === 0 && (
        <EmptyState icon={History} title="Aucun mouvement" text="Les départs et arrivées de cet élevage s’afficheront ici." />
      )}
      <ul className="flex flex-col gap-4">
        {movements.map((movement) => (
          <MovementCard
            key={movement.id}
            movement={movement}
            centerId={center.id}
            onDone={(status) => {
              setLastStatus(status)
              setReloadKey((key) => key + 1)
            }}
          />
        ))}
      </ul>
    </section>
  )
}
