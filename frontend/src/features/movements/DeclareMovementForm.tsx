import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import {
  ArrowLeftRight,
  Check,
  History,
  CircleAlert,
  CircleCheck,
  KeyRound,
  PawPrint,
  ShoppingBag,
  Users,
  Warehouse,
} from 'lucide-react'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { messages, mots } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { identityApi, type UnitItem } from '@/features/identity/api'
import { QrScanner } from '@/features/identity/QrScanner'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'

import { SyncStatusBanner } from '../../components/SyncStatusBanner'
import { movementApi, type ResolvedDestination } from './api'

const MOVEMENT_OPTIONS = [
  { id: 'transfer', label: 'Transfert', icon: ArrowLeftRight },
  { id: 'sale', label: 'Vente', icon: ShoppingBag },
  { id: 'slaughter', label: 'Abattage', icon: Warehouse },
] as const

type MovementType = (typeof MOVEMENT_OPTIONS)[number]['id']

interface SavedDeclaration {
  id: string
  count: number
  heads: number
  destination: string
  movementType: MovementType
}

export function DeclareMovementForm() {
  const navigate = useNavigate()
  const centersResource = useResource(identityApi.centers, 'centres')
  const centers = centersResource.data ?? []
  const [fromCenterId, setFromCenterId] = useState('')
  const fromCenter = centers.find((center) => center.id === fromCenterId) ?? centers[0]
  const unitsResource = useResource(
    () => identityApi.centerUnits(fromCenter?.id ?? ''),
    fromCenter?.id ?? null,
  )
  const units = unitsResource.data ?? []

  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([])
  const [toCenterId, setToCenterId] = useState('')
  const [destinationNote, setDestinationNote] = useState('')
  const [destinationCode, setDestinationCode] = useState('')
  const [resolvedDestination, setResolvedDestination] = useState<ResolvedDestination | null>(null)
  const [resolvingDestination, setResolvingDestination] = useState(false)
  const [movementType, setMovementType] = useState<MovementType>('transfer')
  const [savedDeclaration, setSavedDeclaration] = useState<SavedDeclaration | null>(null)
  const [operationStatus, setOperationStatus] = useState<OperationStatus>('pending')
  const [confirmationCode, setConfirmationCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!savedDeclaration) return
    return subscribeOperation(savedDeclaration.id, (operation) => {
      if (!operation) return
      setOperationStatus(operation.status === 'sending' ? 'pending' : operation.status)
      const response = operation.response
      if (response && typeof response === 'object' && 'confirmation_code' in response) {
        const code = (response as { confirmation_code?: unknown }).confirmation_code
        if (typeof code === 'string') setConfirmationCode(code)
      }
    })
  }, [savedDeclaration])

  const destinations = centers.filter((center) => center.id !== fromCenter?.id)
  const selectedUnits = units.filter((unit) => selectedUnitIds.includes(unit.id))
  const declaredHeads = selectedUnits.reduce((sum, unit) => sum + unit.size, 0)
  const transferNeedsRegisteredCenter = movementType === 'transfer'
  const selectedDestinationCenterId = resolvedDestination?.center_id ?? toCenterId
  const destination = resolvedDestination?.center_name ??
    destinations.find((center) => center.id === toCenterId)?.name ?? destinationNote.trim()

  const resolveDestinationCode = async (rawCode = destinationCode) => {
    const code = rawCode.trim().replace(/^BAOBIA-CENTER:/i, '')
    if (!code) return
    setError(null)
    setResolvingDestination(true)
    try {
      const target = await movementApi.resolveDestinationCode(code)
      setResolvedDestination(target)
      setToCenterId('')
      setDestinationNote('')
      setDestinationCode(code)
    } catch (caught) {
      setResolvedDestination(null)
      setError(caught instanceof ApiError ? caught.message : 'Ce code de partage est invalide ou expiré.')
    } finally {
      setResolvingDestination(false)
    }
  }

  const toggleUnit = (id: string) => {
    setSelectedUnitIds((current) =>
      current.includes(id) ? current.filter((unitId) => unitId !== id) : [...current, id],
    )
  }

  const saveDeclaration = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (
      !fromCenter ||
      selectedUnits.length === 0 ||
      !destination ||
      (transferNeedsRegisteredCenter && !selectedDestinationCenterId)
    ) {
      setError(messages.champManquant)
      return
    }

    const operationId = newUuid()
    setSaving(true)
    try {
      await submit({
        id: operationId,
        type: 'movement.declare',
        path: '/movements/',
        method: 'POST',
        body: {
          id: operationId,
          from_center_id: fromCenter.id,
          ...(selectedDestinationCenterId ? { to_center_id: selectedDestinationCenterId } : {}),
          to_party_note: destination,
          movement_type: movementType,
          items: selectedUnits.map((unit) => ({
            unit_id: unit.id,
            quantity_sent: unit.size,
          })),
          occurred_at: new Date().toISOString(),
        },
      })

      setOperationStatus('pending')
      setSavedDeclaration({
        id: operationId,
        count: selectedUnits.length,
        heads: declaredHeads,
        destination,
        movementType,
      })
    } catch (submitError) {
      setError(
        submitError instanceof ApiError ? submitError.message : 'La déclaration n’a pas pu être gardée sur ce téléphone.',
      )
    } finally {
      setSaving(false)
    }
  }

  const reset = () => {
    setSavedDeclaration(null)
    setOperationStatus('pending')
    setConfirmationCode(null)
    setSelectedUnitIds([])
    setToCenterId('')
    setDestinationNote('')
    setDestinationCode('')
    setResolvedDestination(null)
  }

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (centers.length === 0) {
    return <EmptyState icon={Warehouse} title={messages.aucunElevage} text={messages.aucunElevageAide} />
  }

  if (savedDeclaration) {
    const movementLabel = MOVEMENT_OPTIONS.find((option) => option.id === savedDeclaration.movementType)?.label
    return (
      <section className="flex flex-col gap-5 rounded-xl border-2 border-border bg-surface p-5 shadow-card">
        <SyncStatusBanner status={operationStatus} />
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <CircleCheck aria-hidden className="size-16 text-success" />
          <h1 className="text-title font-bold text-foreground">Départ enregistré</h1>
          <p className="text-body text-muted-foreground">
            La déclaration est gardée sur ce téléphone. L’état d’envoi est indiqué ci-dessus.
          </p>
        </div>
        {confirmationCode && (
          <Banner variant="success" title="Code de confirmation à transmettre">
            {confirmationCode}
          </Banner>
        )}
        <dl className="grid gap-3 rounded-lg border border-border bg-background p-4 text-small">
          <div className="flex justify-between gap-4 border-b border-border pb-2">
            <dt className="font-bold text-muted-foreground">Référence</dt>
            <dd className="max-w-[65%] break-all text-right font-mono text-small font-bold text-primary" aria-label="Identifiant complet du mouvement">
              {savedDeclaration.id}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Origine</dt>
            <dd className="text-right font-bold">{fromCenter?.name}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Destination</dt>
            <dd className="text-right font-bold">{savedDeclaration.destination}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Motif</dt>
            <dd className="font-bold">{movementLabel}</dd>
          </div>
          <div className="flex justify-between gap-4 border-t border-border pt-2">
            <dt className="text-muted-foreground">Animaux déclarés</dt>
            <dd className="font-bold">{savedDeclaration.count} unités · {savedDeclaration.heads} têtes</dd>
          </div>
        </dl>
        <Button icon={CircleAlert} variant="secondary" fullWidth onClick={reset}>
          Nouvelle déclaration
        </Button>
      </section>
    )
  }

  return (
    <form onSubmit={saveDeclaration} className="flex flex-col gap-6">
      {error && <Banner variant="error">{error}</Banner>}

      <h1 className="text-title font-bold text-foreground">{mots.mouvements}</h1>
      <Button type="button" icon={History} variant="ghost" onClick={() => navigate('/mouvements/historique')}>
        Mes mouvements
      </Button>

      {centers.length > 1 ? (
        <Field label="Élevage de départ" required>
          <Select
            value={fromCenter?.id ?? ''}
            onChange={(event) => {
              setFromCenterId(event.target.value)
              setSelectedUnitIds([])
              setToCenterId('')
              setResolvedDestination(null)
              setDestinationCode('')
            }}
            options={centers.map((center) => ({ value: center.id, label: center.name }))}
          />
        </Field>
      ) : (
        <p className="text-body font-bold text-foreground">Élevage de départ · {fromCenter?.name}</p>
      )}

      <section className="flex flex-col gap-3" aria-labelledby="units-heading">
        <h2 id="units-heading" className="text-subtitle font-bold text-foreground">Quels animaux partent ?</h2>
        {unitsResource.loading && <Loader />}
        {unitsResource.error && <Banner variant="error">{unitsResource.error.message}</Banner>}
        {unitsResource.data?.length === 0 && (
          <EmptyState icon={PawPrint} title={messages.aucunAnimal} text={messages.aucunAnimalAide} />
        )}
        {units.length > 0 && (
          <ul className="flex flex-col gap-2">
            {units.map((unit: UnitItem) => {
              const selected = selectedUnitIds.includes(unit.id)
              const UnitIcon = unit.kind === 'lot' ? Users : PawPrint
              return (
                <li key={unit.id}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleUnit(unit.id)}
                    className={`flex min-h-touch w-full items-center gap-3 rounded-md border-2 p-3 text-left transition-colors ${
                      selected ? 'border-primary bg-accent' : 'border-border bg-surface hover:border-primary'
                    }`}
                  >
                    <UnitIcon aria-hidden className="size-icon shrink-0 text-primary" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-small font-bold text-foreground">
                        {unit.label_code || unit.local_name || unit.species.label_fr}
                      </span>
                      <span className="block text-caption text-muted-foreground">
                        {unit.species.label_fr} · {unit.kind === 'lot' ? `${unit.size} têtes` : 'Animal'}
                      </span>
                    </span>
                    {selected && <Check aria-hidden className="size-icon shrink-0 text-primary" />}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
        <p className="text-small font-bold text-primary">
          {selectedUnitIds.length === 0
            ? 'Aucun animal sélectionné'
            : `${selectedUnitIds.length} unité${selectedUnitIds.length > 1 ? 's' : ''} · ${declaredHeads} tête${declaredHeads > 1 ? 's' : ''}`}
        </p>
      </section>

      <section className="flex flex-col gap-3" aria-labelledby="type-heading">
        <h2 id="type-heading" className="text-subtitle font-bold text-foreground">Motif du départ</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {MOVEMENT_OPTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              aria-pressed={movementType === id}
              onClick={() => {
                setMovementType(id)
                if (id === 'transfer') setDestinationNote('')
                if (id !== 'transfer') {
                  setResolvedDestination(null)
                  setDestinationCode('')
                }
              }}
              className={`flex min-h-touch items-center justify-center gap-2 rounded-md border-2 px-3 font-bold text-small ${
                movementType === id
                  ? 'border-primary bg-accent text-primary'
                  : 'border-border bg-surface text-foreground'
              }`}
            >
              <Icon aria-hidden className="size-icon" />
              {label}
            </button>
          ))}
        </div>
      </section>

      <Field
        label="Destination"
        help={
          transferNeedsRegisteredCenter
            ? 'Choisissez un élevage de votre liste ou utilisez le code/QR partagé par le destinataire.'
            : 'Choisissez un élevage enregistré ou indiquez le lieu de vente ou d’abattage.'
        }
        required={!destinations.length}
      >
        {transferNeedsRegisteredCenter && resolvedDestination ? (
          <Banner variant="success" title="Élevage destinataire vérifié">
            {resolvedDestination.center_name}{' '}
            <button type="button" className="underline" onClick={() => setResolvedDestination(null)}>Changer</button>
          </Banner>
        ) : destinations.length > 0 && (
          <Select
            value={toCenterId}
            onChange={(event) => {
              setToCenterId(event.target.value)
              setResolvedDestination(null)
              setDestinationCode('')
              setDestinationNote('')
            }}
            placeholder="Choisir un élevage"
            options={destinations.map((center) => ({ value: center.id, label: center.name }))}
          />
        )}
        {transferNeedsRegisteredCenter && !resolvedDestination && (
          <Banner variant="warning">
            Le destinataire peut partager son code ou son QR. Scannez-le ou collez le code ci-dessous.
          </Banner>
        )}
        {transferNeedsRegisteredCenter && !resolvedDestination && (
          <>
            <Field label="Code de partage du destinataire" help="Vous pouvez aussi scanner son QR code.">
              <input
                aria-label="Code de partage du destinataire"
                className="h-touch-secondary w-full rounded-md border-2 border-input bg-surface px-4 font-mono text-caption text-foreground focus-visible:border-ring"
                value={destinationCode}
                onChange={(event) => {
                  setDestinationCode(event.target.value)
                  setResolvedDestination(null)
                  setToCenterId('')
                }}
                autoCapitalize="none"
                spellCheck={false}
              />
            </Field>
            <QrScanner onCode={(value) => {
              setDestinationCode(value.replace(/^BAOBIA-CENTER:/i, ''))
              void resolveDestinationCode(value)
            }} />
            <Button type="button" icon={KeyRound} variant="secondary" fullWidth loading={resolvingDestination} disabled={!destinationCode.trim()} onClick={() => void resolveDestinationCode()}>
              Vérifier le code
            </Button>
          </>
        )}
        {!toCenterId && !transferNeedsRegisteredCenter && (
          <input
            aria-label="Autre destination"
            className="h-touch-secondary w-full rounded-md border-2 border-input bg-surface px-4 text-body text-foreground placeholder:text-muted-foreground focus-visible:border-ring"
            value={destinationNote}
            onChange={(event) => setDestinationNote(event.target.value)}
            placeholder="Marché ou autre lieu"
            required
          />
        )}
      </Field>

      <Button
        type="submit"
        icon={ArrowLeftRight}
        fullWidth
        loading={saving}
        disabled={
          !fromCenter ||
          selectedUnitIds.length === 0 ||
          !destination ||
          (transferNeedsRegisteredCenter && !selectedDestinationCenterId)
        }
      >
        Déclarer
      </Button>
    </form>
  )
}
