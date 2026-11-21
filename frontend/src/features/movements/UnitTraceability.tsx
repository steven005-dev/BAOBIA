/**
 * Sur la fiche de l'animal (guide de réalisation des ajouts, 21/11) :
 * - Ajout 1 : la boucle officielle Vet'Tronic (RFID, 15 chiffres), saisie ou scannée.
 * - Ajout 4 : le parcours de l'animal, chaque mouvement marqué « Sûr » ou « Probable ».
 * Un élevage auquel la personne n'a pas accès reste anonyme (« Élevage » et sa zone).
 * Module mouvements (Konan Romuald) ; la fiche (identity) ne fait que l'afficher.
 */

import { useEffect, useState } from 'react'
import { ArrowDown, Keyboard, Nfc, Radio, ScanLine, Tag } from 'lucide-react'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { newUuid } from '@/lib/uuid'
import { erreurs } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { QrScanner } from '@/features/identity/QrScanner'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'

import { formatRfid, normalizeRfid, tracingApi, type Place, type RfidReadMode, type RouteStep } from './api'

const READ_MODES: Record<RfidReadMode, { label: string; icon: typeof Nfc; trust: string }> = {
  rfid_reader: { label: 'Lu par un lecteur RFID', icon: Radio, trust: 'vérifiée' },
  code_scan: { label: 'Code imprimé scanné', icon: ScanLine, trust: 'vérifiée' },
  manual_entry: { label: 'Numéro saisi à la main', icon: Keyboard, trust: 'déclarée' },
}

function formatDay(value: string) {
  return new Date(value).toLocaleDateString('fr-CI', { day: 'numeric', month: 'long', year: 'numeric' })
}

function placeText(place: Place) {
  if (place.type === null) return place.detail ? `Hors système · ${place.detail}` : 'Hors système'
  return place.zone ? `${place.label} · ${place.zone}` : place.label
}

function ConfidenceBadge({ step }: { step: RouteStep }) {
  const sure = step.confidence === 'confirmed'
  const counted = step.confidence !== null
  const classes = sure
    ? 'border-success bg-success-bg text-success'
    : counted ? 'border-warning bg-warning-bg text-warning' : 'border-border bg-surface text-muted-foreground'
  return (
    <span className={`inline-flex min-h-8 items-center rounded-full border-2 px-3 text-caption font-bold ${classes}`}>
      {step.confidence_label}
    </span>
  )
}

function RfidForm({ unitId, onDone }: { unitId: string; onDone: () => void }) {
  const [digits, setDigits] = useState('')
  const [mode, setMode] = useState<RfidReadMode>('manual_entry')
  const [operationId, setOperationId] = useState<string | null>(null)
  const [status, setStatus] = useState<OperationStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!operationId) return
    return subscribeOperation(operationId, (operation) => {
      if (!operation) return
      const next = operation.status === 'sending' ? 'pending' : operation.status
      setStatus(next)
      if (next === 'check') setError(operation.last_error ?? erreurs.saisie)
      if (next === 'sent') onDone()
    })
  }, [operationId, onDone])

  const number = normalizeRfid(digits)
  const save = async () => {
    if (!number) return
    const id = newUuid()
    setError(null)
    await submit({ id, type: 'rfid_tag.bind', path: '/rfid-tags/', method: 'POST',
                   body: { id, unit_id: unitId, number, read_mode: mode } })
    setOperationId(id)
  }

  return (
    <div className="flex flex-col gap-3">
      <QrScanner onCode={(code) => {
        const scanned = normalizeRfid(code)
        if (scanned) {
          setDigits(scanned)
          setMode('code_scan')
          setError(null)
        } else {
          setError('Ce code n’est pas un numéro de boucle (15 chiffres).')
        }
      }} />
      <Field label="Numéro de la boucle" help={`${digits.length} / 15 chiffres`}>
        <Input
          inputMode="numeric"
          placeholder="384 000 000 000 000"
          value={formatRfid(digits)}
          onChange={(event) => {
            setDigits(event.target.value.replace(/\D/g, '').slice(0, 15))
            setMode('manual_entry')
          }}
        />
      </Field>
      {number && !number.startsWith('384') && (
        <Banner variant="warning">Vérifiez le numéro : une boucle ivoirienne commence par 384.</Banner>
      )}
      {error && <Banner variant="error">{error}</Banner>}
      {status === 'pending' && <Banner variant="info">En attente d’envoi.</Banner>}
      <Button icon={Tag} fullWidth disabled={!number || status === 'pending'} onClick={() => void save()}>
        Enregistrer la boucle
      </Button>
    </div>
  )
}

export function UnitTraceability({ unitId, isAnimal }: { unitId: string; isAnimal: boolean }) {
  const [reload, setReload] = useState(0)
  const [editing, setEditing] = useState(false)
  const { data, error, loading } = useResource(() => tracingApi.route(unitId), `parcours-${unitId}-${reload}`)

  if (loading && !data) return <Loader />
  if (error || !data) return null
  const mode = data.rfid ? READ_MODES[data.rfid.read_mode] : null

  return (
    <>
      {isAnimal && (
        <section aria-labelledby="rfid-heading" className="flex flex-col gap-3 rounded-xl border-2 border-border bg-surface p-4">
          <h2 id="rfid-heading" className="text-subtitle font-bold text-foreground">Boucle officielle</h2>
          {data.rfid && mode && !editing && (
            <>
              <p className="text-number font-bold tracking-wide text-foreground">{data.rfid.number}</p>
              <p className="inline-flex items-center gap-2 text-small text-muted-foreground">
                <mode.icon aria-hidden className="size-icon-badge" />
                {mode.label} · identité {mode.trust}
              </p>
            </>
          )}
          {!data.rfid && !editing && (
            <p className="text-body text-muted-foreground">Aucune boucle RFID enregistrée pour cet animal.</p>
          )}
          {editing ? (
            <RfidForm unitId={unitId} onDone={() => { setEditing(false); setReload((n) => n + 1) }} />
          ) : (
            <Button variant="secondary" icon={Nfc} onClick={() => setEditing(true)}>
              {data.rfid ? 'Remplacer la boucle' : 'Ajouter le numéro de la boucle officielle'}
            </Button>
          )}
        </section>
      )}

      <section aria-labelledby="route-heading" className="flex flex-col gap-3">
        <h2 id="route-heading" className="text-subtitle font-bold text-foreground">Parcours</h2>
        {data.steps.length === 0 ? (
          <p className="text-body text-muted-foreground">Aucun mouvement enregistré.</p>
        ) : (
          <ol className="flex flex-col gap-3">
            {data.steps.map((step) => (
              <li key={step.movement_id} className="flex flex-col gap-2 rounded-xl border-2 border-border bg-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-small font-bold text-foreground">{formatDay(step.occurred_at)}</span>
                  <ConfidenceBadge step={step} />
                </div>
                <p className="text-body text-foreground">{placeText(step.from)}</p>
                <ArrowDown aria-hidden className="size-icon-badge text-muted-foreground" />
                <p className="text-body text-foreground">{placeText(step.to)}</p>
                {step.confidence === 'one_side' && (
                  <p className="text-small text-muted-foreground">
                    {step.declared_by === 'receiver' ? 'Déclaré à l’arrivée seulement.' : 'Déclaré d’un seul côté.'}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  )
}
