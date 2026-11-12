import { useState } from 'react'
import { ArrowLeftRight, CheckCircle, Package, Warehouse } from 'lucide-react'
import { enqueueOperation } from '../offline/enqueueOperation'
import { SyncStatusBanner } from '../../components/SyncStatusBanner'
import type { OperationStatus } from '../offline/types'

interface AnimalChoice {
  id: string
  label: string
  species: string
}

interface DeclareMovementFormProps {
  fromCenterName?: string
  fromCenterId?: string
  availableAnimals?: AnimalChoice[]
  onSuccess?: (operationId: string) => void
}

export const DeclareMovementForm: React.FC<DeclareMovementFormProps> = ({
  fromCenterName = 'Élevage Principal (Abidjan)',
  fromCenterId = 'center-origin-demo',
  availableAnimals = [
    { id: 'unit-cattle-01', label: 'Bovin #4892 (Taureau)', species: 'Bovin' },
    { id: 'unit-cattle-02', label: 'Bovin #4893 (Génisse)', species: 'Bovin' },
    { id: 'unit-sheep-01', label: 'Ovin #1024 (Bélier)', species: 'Ovin' },
  ],
  onSuccess,
}) => {
  const [toCenterName, setToCenterName] = useState('')
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([])
  const [movementType, setMovementType] = useState('transfer')
  const [status, setStatus] = useState<OperationStatus | null>(null)
  const [lastOpId, setLastOpId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const toggleSelectUnit = (id: string) => {
    setSelectedUnitIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg('')

    if (!toCenterName.trim()) {
      setErrorMsg('Veuillez indiquer l’élevage de destination.')
      return
    }

    if (selectedUnitIds.length === 0) {
      setErrorMsg('Veuillez sélectionner au moins un animal.')
      return
    }

    setIsSubmitting(true)

    try {
      // Construction du payload conforme au backend BAOBIA
      const payload = {
        from_center_id: fromCenterId,
        to_party_note: toCenterName.trim(),
        movement_type: movementType,
        items: selectedUnitIds.map((id) => ({
          unit_id: id,
          quantity_sent: 1,
        })),
        occurred_at: new Date().toISOString(),
      }

      // Écriture par la fonction unique enqueueOperation()
      const opId = await enqueueOperation('movement.declare', payload)
      setLastOpId(opId)
      setStatus('pending')

      if (onSuccess) {
        onSuccess(opId)
      }
    } catch (err) {
      setErrorMsg('Impossible d’enregistrer la déclaration sur l’appareil.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto p-4 flex flex-col gap-5 bg-[var(--surface)] rounded-2xl border border-[var(--border)] shadow-sm">
      {/* En-tête de l'écran */}
      <div className="flex items-center gap-3 border-b border-[var(--border)] pb-3">
        <div className="p-3 bg-[var(--brand-light)] text-[var(--brand)] rounded-xl">
          <ArrowLeftRight className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--foreground)]">Déclarer un départ</h1>
          <p className="text-sm text-[var(--text-secondary)]">Transfert ou vente d'animaux</p>
        </div>
      </div>

      {/* Bannière d'état de synchronisation */}
      {status && <SyncStatusBanner status={status} />}

      {/* Message d'erreur s'il y en a */}
      {errorMsg && (
        <div className="p-3 bg-[var(--error-bg)] text-[var(--error)] rounded-lg text-sm font-semibold border border-[#E8BACB]">
          {errorMsg}
        </div>
      )}

      {/* Écran de succès après enregistrement local */}
      {lastOpId && status === 'pending' ? (
        <div className="p-4 bg-[var(--brand-light)] rounded-xl flex flex-col gap-3 text-center items-center">
          <CheckCircle className="w-12 h-12 text-[var(--brand)]" />
          <h2 className="text-lg font-bold text-[var(--brand)]">Transfert enregistré</h2>
          <p className="text-sm text-[var(--foreground)]">
            Votre déclaration est enregistrée en sécurité sur ce téléphone et sera transmise dès que possible.
          </p>
          <button
            type="button"
            onClick={() => {
              setLastOpId(null)
              setStatus(null)
              setSelectedUnitIds([])
              setToCenterName('')
            }}
            className="btn-secondary w-full mt-2"
          >
            Faire un autre départ
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* Élevage de départ (verrouillé) */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-bold text-[var(--text-secondary)]">Élevage de départ</label>
            <div className="flex items-center gap-2 p-3 bg-[var(--surface-secondary)] rounded-xl text-base font-semibold text-[var(--foreground)]">
              <Warehouse className="w-5 h-5 text-[var(--brand)]" />
              <span>{fromCenterName}</span>
            </div>
          </div>

          {/* Type de mouvement */}
          <div className="flex flex-col gap-1">
            <label htmlFor="movement_type" className="text-sm font-bold text-[var(--text-secondary)]">Motif du départ</label>
            <select
              id="movement_type"
              value={movementType}
              onChange={(e) => setMovementType(e.target.value)}
              className="min-h-[48px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-base font-semibold"
            >
              <option value="transfer">Transfert vers un autre élevage</option>
              <option value="sale">Vente au marché</option>
              <option value="slaughter">Abattage</option>
            </select>
          </div>

          {/* Élevage ou acheteur destinataire */}
          <div className="flex flex-col gap-1">
            <label htmlFor="destination_input" className="text-sm font-bold text-[var(--text-secondary)]">
              Destination / Élevage destinataire *
            </label>
            <input
              id="destination_input"
              type="text"
              placeholder="Ex : Élevage de Korhogo ou Marché de Bouaké"
              value={toCenterName}
              onChange={(e) => setToCenterName(e.target.value)}
              className="min-h-[48px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-base"
              required
            />
          </div>

          {/* Sélection des animaux */}
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-bold text-[var(--text-secondary)]">
                Animaux à transférer *
              </label>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-[var(--brand-light)] text-[var(--brand)]">
                {selectedUnitIds.length} sélectionné(s)
              </span>
            </div>

            <div className="flex flex-col gap-2 max-h-56 overflow-y-auto">
              {availableAnimals.map((animal) => {
                const isSelected = selectedUnitIds.includes(animal.id)
                return (
                  <button
                    key={animal.id}
                    type="button"
                    onClick={() => toggleSelectUnit(animal.id)}
                    className={`flex items-center justify-between p-3 rounded-xl border min-h-[48px] text-left transition-colors ${
                      isSelected
                        ? 'border-[var(--brand)] bg-[var(--brand-light)] text-[var(--brand)]'
                        : 'border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Package className="w-5 h-5 flex-shrink-0" />
                      <div>
                        <div className="font-bold text-sm">{animal.label}</div>
                        <div className="text-xs opacity-75">{animal.species}</div>
                      </div>
                    </div>
                    <div
                      className={`w-5 h-5 rounded border flex items-center justify-center font-bold text-xs ${
                        isSelected ? 'bg-[var(--brand)] text-white border-[var(--brand)]' : 'border-[var(--border)]'
                      }`}
                    >
                      {isSelected ? '✓' : ''}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Action principale : 60px de haut, icône + mot court */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full mt-2"
          >
            <ArrowLeftRight className="w-6 h-6" />
            <span>{isSubmitting ? 'Enregistrement...' : 'Transférer'}</span>
          </button>
        </form>
      )}
    </div>
  )
}
