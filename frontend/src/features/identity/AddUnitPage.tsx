/**
 * Ajouter un animal ou un lot (gabarit Formulaire en une action) : une question par écran.
 * Étapes : espèce -> animal ou lot (si l'espèce permet les deux) -> nombre (lot) -> étiquette.
 * Étiquette (21/11) : pour un animal, voie principale = NUMÉRO OFFICIEL de la boucle (15 chiffres,
 * Vet'Tronic) ; un code QR BAOBIA est créé en plus (étiquette, scan). Autres voies : scanner la
 * boucle BAOBIA préimprimée, ou code créé par le téléphone (lots, porcs, volailles, secours).
 * L'identifiant et le code sont créés une seule fois : un double envoi est sans effet.
 */

import { ArrowLeft, ArrowRight, BadgeCheck, CirclePlus, PawPrint, QrCode, ScanQrCode, Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { CodeInput } from '@/components/CodeInput'
import { Input } from '@/components/Input'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { NumberStepper } from '@/components/NumberStepper'
import { useToast } from '@/components/Toast'
import { normalizeRfid } from '@/features/movements/api'
import { submit } from '@/offline'
import { ApiError } from '@/lib/api'
import { generateShortCode, isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, newUuid, type Species, type UnitKind } from './api'
import { LabelToPrint } from './LabelToPrint'
import { QrScanner } from './QrScanner'
import { speciesIcon } from './speciesIcon'
import { useResource } from './useResource'

type Step = 'species' | 'kind' | 'size' | 'label'
type LabelMode = 'official' | 'tag' | 'generate'

function stepsFor(species: Species | undefined, kind: UnitKind): Step[] {
  const steps: Step[] = ['species']
  if (species?.tracking_mode === 'both') steps.push('kind')
  if (kind === 'lot') steps.push('size')
  steps.push('label')
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
  const [labelChoice, setLabelChoice] = useState<LabelMode | null>(null)
  const [tagCode, setTagCode] = useState('')
  const [officialDigits, setOfficialDigits] = useState('')
  const [officialRead, setOfficialRead] = useState<'code_scan' | 'manual_entry'>('manual_entry')
  const [stepIndex, setStepIndex] = useState(0)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [queued, setQueued] = useState(false)

  const chosen = species.data?.find((s) => s.id === speciesId)
  const kind = kindChoice ?? defaultKind(chosen)
  const steps = stepsFor(chosen, kind)
  const step = steps[Math.min(stepIndex, steps.length - 1)]
  const isLast = stepIndex >= steps.length - 1
  // La boucle officielle se pose sur un animal (pas un lot) : c'est le choix proposé d'abord.
  const officialAllowed = kind === 'animal'
  const labelMode: LabelMode = labelChoice ?? (officialAllowed ? 'official' : 'tag')
  const officialNumber = normalizeRfid(officialDigits)

  const canContinue =
    (step === 'species' && !!chosen) ||
    step === 'kind' ||
    (step === 'size' && size >= 1) ||
    (step === 'label' && (labelMode === 'generate' || (labelMode === 'official' ? !!officialNumber
      : isValidShortCode(tagCode))))

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
      const useTag = labelMode === 'tag'
      let result = await identityApi.addUnit(unitId, unit(useTag ? tagCode : code))
      if (!useTag && result.status === 'check' && result.error?.includes('déjà posée')) {
        // Code déjà pris (doublon, en pratique impossible) : on en crée un autre et on réessaie
        // une fois. Le même identifiant d'animal est gardé : rien n'a été créé au premier essai.
        const fresh = generateShortCode()
        setCode(fresh)
        result = await identityApi.addUnit(unitId, unit(fresh))
      }
      if (labelMode === 'official' && officialNumber && result.status !== 'check') {
        // Boucle officielle, enregistrée par le module traceability (file hors ligne comprise).
        const tagId = newUuid()
        await submit({ id: tagId, type: 'rfid_tag.bind', path: '/rfid-tags/', method: 'POST',
                       body: { id: tagId, unit_id: unitId, number: officialNumber, read_mode: officialRead } })
      }
      if (result.status === 'sent') {
        toast.show(kind === 'lot' ? messages.lotAjoute : messages.animalAjoute, 'success')
        navigate(`/centres/animaux/${unitId}`, { replace: true })
      } else if (result.status === 'check') {
        setError(result.error ?? erreurs.saisie)
      } else {
        setQueued(true) // hors ligne : gardé sur le téléphone, l'étiquette est déjà imprimable
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  const next = () => {
    if (!canContinue) {
      setError(step === 'label' ? messages.scannezLaBoucle : messages.champManquant)
      return
    }
    setError(null)
    if (isLast) void send()
    else setStepIndex(stepIndex + 1)
  }

  if (queued && chosen) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-title font-bold text-foreground">{titres.ajouterAnimal}</h1>
        <Banner variant="info" title={messages.enAttente}>
          {messages.gardeSurTelephone} {labelMode === 'generate' && messages.etiquetteDejaImprimable}
        </Banner>
        {labelMode === 'generate' && <LabelToPrint code={code} species={chosen.label_fr} />}
        <Button icon={PawPrint} onClick={() => navigate(`/centres?elevage=${centerId}`, { replace: true })}>
          {mots.animaux}
        </Button>
      </div>
    )
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

      {step === 'label' && (
        <div className="flex flex-col gap-4">
          <ChoiceGrid
            label={titres.quelleEtiquette}
            value={labelMode}
            onChange={(value) => {
              setLabelChoice(value as LabelMode)
              setError(null)
            }}
            options={[
              ...(officialAllowed ? [{ value: 'official', label: champs.boucleOfficielle, icon: BadgeCheck }] : []),
              { value: 'tag', label: champs.scannerBoucle, icon: ScanQrCode },
              { value: 'generate', label: champs.creerCode, icon: QrCode },
            ]}
          />
          {labelMode === 'official' && (
            <>
              <QrScanner
                onCode={(raw) => {
                  const value = normalizeRfid(raw)
                  if (!value) return setError(messages.etiquetteNonReconnue)
                  setOfficialDigits(value)
                  setOfficialRead('code_scan')
                  setError(null)
                  toast.show(messages.boucleLue, 'success')
                }}
              />
              <Field label={champs.numeroOfficiel} help={champs.numeroOfficielAide}>
                <Input inputMode="numeric" autoComplete="off" value={officialDigits}
                       onChange={(e) => { setOfficialDigits(e.target.value); setOfficialRead('manual_entry') }} />
              </Field>
            </>
          )}
          {labelMode === 'tag' && (
            <>
              <QrScanner
                onCode={(raw) => {
                  const value = normalizeShortCode(raw)
                  if (!isValidShortCode(value)) return setError(messages.etiquetteNonReconnue)
                  setTagCode(value)
                  setError(null)
                  toast.show(messages.boucleLue, 'success')
                }}
              />
              <Field
                label={champs.codeEtiquette}
                help={champs.codeEtiquetteAide}
                error={tagCode.length === 9 && !isValidShortCode(tagCode) ? erreurs.codeIncorrect : null}
              >
                <CodeInput value={tagCode} onValueChange={setTagCode} />
              </Field>
            </>
          )}
        </div>
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
