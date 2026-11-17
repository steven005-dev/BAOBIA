/**
 * Ajouter un animal ou un lot (gabarit Formulaire en une action) : une question par écran.
 * Étapes : espèce -> animal ou lot (si l'espèce permet les deux) -> nombre (lot).
 * Le code de l'étiquette est CRÉÉ PAR LE TÉLÉPHONE (personne ne le saisit) ; la fiche
 * l'affiche ensuite en grand pour faire l'étiquette physique.
 * L'identifiant et le code sont créés une seule fois : un double envoi est sans effet.
 */

import { ArrowLeft, ArrowRight, CirclePlus, PawPrint, Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { Loader } from '@/components/Loader'
import { NumberStepper } from '@/components/NumberStepper'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { generateShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, newUuid, type Species, type UnitKind } from './api'
import { speciesIcon } from './speciesIcon'
import { useResource } from './useResource'

type Step = 'species' | 'kind' | 'size'

function stepsFor(species: Species | undefined, kind: UnitKind): Step[] {
  const steps: Step[] = ['species']
  if (species?.tracking_mode === 'both') steps.push('kind')
  if (kind === 'lot') steps.push('size')
  return steps
}

function defaultKind(species: Species | undefined): UnitKind {
  return species?.tracking_mode === 'lot' ? 'lot' : 'animal'
}

export function AddUnitPage() {
  const { centerId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const species = useResource(identityApi.species, 'especes')

  const [unitId] = useState(newUuid)
  const [speciesId, setSpeciesId] = useState<string | null>(null)
  const [kindChoice, setKindChoice] = useState<UnitKind | null>(null)
  const [size, setSize] = useState(1)
  const [code, setCode] = useState(generateShortCode)
  const [stepIndex, setStepIndex] = useState(0)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chosen = species.data?.find((s) => s.id === speciesId)
  const kind = kindChoice ?? defaultKind(chosen)
  const steps = stepsFor(chosen, kind)
  const step = steps[Math.min(stepIndex, steps.length - 1)]
  const isLast = stepIndex >= steps.length - 1

  const canContinue =
    (step === 'species' && !!chosen) ||
    step === 'kind' ||
    (step === 'size' && size >= 1)

  const back = () => {
    setError(null)
    if (stepIndex === 0) navigate(-1)
    else setStepIndex(stepIndex - 1)
  }

  const send = async () => {
    if (!chosen) return
    setSending(true)
    setError(null)
    const unit = (labelCode: string) => ({
      kind,
      center_id: centerId,
      species_id: chosen.id,
      label_code: labelCode,
      ...(kind === 'lot' ? { size } : {}),
    })
    try {
      try {
        await identityApi.addUnit(unitId, unit(code))
      } catch (err) {
        // Code déjà pris (doublon, en pratique impossible) : on en crée un autre et on réessaie
        // une fois. Le même identifiant d'animal est gardé : rien n'a été créé au premier essai.
        const codeTaken = err instanceof ApiError && err.kind === 'validation' && err.message.includes('déjà posée')
        if (!codeTaken) throw err
        const fresh = generateShortCode()
        setCode(fresh)
        await identityApi.addUnit(unitId, unit(fresh))
      }
      toast.show(kind === 'lot' ? messages.lotAjoute : messages.animalAjoute, 'success')
      navigate(`/centres/animaux/${unitId}`, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  const next = () => {
    if (!canContinue) {
      setError(messages.champManquant)
      return
    }
    setError(null)
    if (isLast) void send()
    else setStepIndex(stepIndex + 1)
  }

  if (species.loading) return <Loader />
  if (species.error) return <Banner variant="error">{species.error.message}</Banner>

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <p className="text-caption font-bold text-muted-foreground">
          {champs.etape} {stepIndex + 1} {champs.sur} {steps.length}
        </p>
        <h1 className="text-title font-bold text-foreground">{titres.ajouterAnimal}</h1>
      </div>

      {step === 'species' && (
        <ChoiceGrid
          label={titres.quelleEspece}
          value={speciesId}
          onChange={(value) => {
            setSpeciesId(value)
            setKindChoice(null)
          }}
          options={(species.data ?? []).map((s) => ({
            value: s.id,
            label: s.label_fr,
            icon: speciesIcon(s.code),
          }))}
        />
      )}

      {step === 'kind' && (
        <ChoiceGrid
          label={titres.animalOuLot}
          value={kind}
          onChange={(value) => setKindChoice(value as UnitKind)}
          options={[
            { value: 'animal', label: mots.animal, icon: PawPrint },
            { value: 'lot', label: mots.lot, icon: Users },
          ]}
        />
      )}

      {step === 'size' && (
        <NumberStepper label={titres.combienAnimaux} value={size} onChange={setSize} min={1} max={10000} />
      )}


      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        <Button icon={isLast ? CirclePlus : ArrowRight} onClick={next} loading={sending}>
          {isLast ? mots.ajouter : mots.continuer}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} onClick={back} disabled={sending}>
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
