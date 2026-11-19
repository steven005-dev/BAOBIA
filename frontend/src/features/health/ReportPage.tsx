/**
 * Signaler un cas (gabarit Formulaire en une action) : une question par écran, choix par
 * icônes, aucun texte à écrire. L'éleveur n'a pas à connaître le nom de la maladie (SA-03).
 * Étapes : élevage (s'il en a plusieurs) -> que se passe-t-il -> signes -> animaux -> nombre.
 * L'identifiant est créé une fois : un double envoi est sans effet (opération rejouable).
 * Hors ligne : gardé sur le téléphone, part tout seul au retour du réseau.
 */

import {
  Activity, ArrowLeft, ArrowRight, Droplet, Droplets, Flag, Footprints, HeartPulse, PawPrint,
  ScanFace, Skull, Thermometer, UtensilsCrossed, Warehouse, Wind, type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { NumberStepper } from '@/components/NumberStepper'
import { useToast } from '@/components/Toast'
import { identityApi } from '@/features/identity/api'
import { currentPosition } from '@/features/identity/position'
import { speciesIcon } from '@/features/identity/speciesIcon'
import { useResource } from '@/features/identity/useResource'
import { ApiError } from '@/lib/api'
import { champs, erreurs, messages, mots, sante, typesSignalement } from '@/lib/vocabulaire'

import { healthApi, newUuid, type ReportKind } from './api'

/** Pictogrammes provisoires des symptômes (charte : à dessiner, testés avec 5 personnes). */
const SYMPTOM_ICONS: Record<string, LucideIcon> = {
  'utensils-crossed': UtensilsCrossed,
  thermometer: Thermometer,
  droplets: Droplets,
  wind: Wind,
  footprints: Footprints,
  'scan-face': ScanFace,
  droplet: Droplet,
  skull: Skull,
}

const KIND_ICONS: Record<ReportKind, LucideIcon> = {
  suspicion: HeartPulse,
  death: Skull,
  abnormal_mortality: Skull,
}

/** Gravité déduite (pas d'étape en plus pour l'éleveur). */
const SEVERITY: Record<ReportKind, 'medium' | 'high'> = {
  suspicion: 'medium',
  death: 'high',
  abnormal_mortality: 'high',
}

type Step = 'center' | 'kind' | 'symptoms' | 'units' | 'count'

export function ReportPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()
  const centers = useResource(identityApi.centers, 'centres')

  const [reportId] = useState(newUuid)
  const [centerId, setCenterId] = useState<string | null>(params.get('elevage'))
  const [kind, setKind] = useState<ReportKind | null>(null)
  const [symptoms, setSymptoms] = useState<string[]>([])
  const [unitIds, setUnitIds] = useState<string[]>([])
  const [count, setCount] = useState(1)
  const [stepIndex, setStepIndex] = useState(0)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [queued, setQueued] = useState(false)

  // Un seul élevage : choisi d'office, pas de question.
  const onlyCenter = centers.data?.length === 1 ? (centers.data[0]?.id ?? null) : null
  const center = centerId ?? onlyCenter
  const units = useResource(() => identityApi.centerUnits(center ?? ''), center)
  const symptomList = useResource(() => healthApi.symptoms(), 'symptomes')

  const steps: Step[] = [
    ...(onlyCenter ? [] : (['center'] as Step[])),
    'kind', 'symptoms',
    ...(units.data && units.data.length > 0 ? (['units'] as Step[]) : []),
    'count',
  ]
  const step = steps[Math.min(stepIndex, steps.length - 1)]
  const isLast = stepIndex >= steps.length - 1

  // Le nombre touché ne peut pas être plus petit que les animaux choisis.
  const affected = Math.max(count, unitIds.length)

  const canContinue =
    (step === 'center' && !!center) || (step === 'kind' && !!kind) ||
    step === 'symptoms' || step === 'units' || (step === 'count' && affected >= 1)

  const send = async () => {
    if (!center || !kind) return
    setSending(true)
    setError(null)
    const position = await currentPosition()
    try {
      const result = await healthApi.submitReport(reportId, {
        center_id: center,
        report_kind: kind,
        affected_count: affected,
        self_severity: SEVERITY[kind],
        occurred_at: new Date().toISOString(),
        symptom_codes: symptoms,
        subjects: unitIds.map((unit_id) => ({ unit_id, condition: kind === 'suspicion' ? 'sick' : 'dead' })),
        ...(position
          ? { latitude: position.latitude, longitude: position.longitude,
              position_accuracy_m: position.accuracy_m, position_source: 'gps' as const }
          : { position_source: 'none' as const }),
      })
      if (result.status === 'sent') {
        toast.show(messages.signalementEnvoye, 'success')
        navigate(`/sante/${reportId}`, { replace: true })
      } else if (result.status === 'check') {
        setError(result.error ?? erreurs.saisie)
      } else {
        setQueued(true)
      }
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

  const back = () => {
    setError(null)
    if (stepIndex === 0) navigate(-1)
    else setStepIndex(stepIndex - 1)
  }

  if (queued) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-title font-bold text-foreground">{sante.titreSignaler}</h1>
        <Banner variant="info" title={messages.enAttente}>{messages.gardeSurTelephone}</Banner>
        <Button icon={Flag} onClick={() => navigate('/sante', { replace: true })}>
          {sante.mesSignalements}
        </Button>
      </div>
    )
  }

  if (centers.loading || symptomList.loading) return <Loader />
  if (centers.error) return <Banner variant="error">{centers.error.message}</Banner>
  if (!centers.data?.length) {
    return <EmptyState icon={Warehouse} title={messages.aucunElevage} text={messages.aucunElevageAide} />
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <p className="text-caption font-bold text-muted-foreground">
          {champs.etape} {stepIndex + 1} {champs.sur} {steps.length}
        </p>
        <h1 className="text-title font-bold text-foreground">{sante.titreSignaler}</h1>
      </div>

      {step === 'center' && (
        <ChoiceGrid
          label={sante.quelElevage}
          value={center}
          onChange={(value) => {
            setCenterId(value)
            setUnitIds([])
          }}
          options={centers.data.map((c) => ({ value: c.id, label: c.name, icon: Warehouse }))}
        />
      )}

      {step === 'kind' && (
        <ChoiceGrid
          label={sante.queSePasseTIl}
          value={kind}
          onChange={(value) => setKind(value as ReportKind)}
          options={(Object.keys(typesSignalement) as ReportKind[]).map((k) => ({
            value: k, label: typesSignalement[k], icon: KIND_ICONS[k],
          }))}
        />
      )}

      {step === 'symptoms' && (
        <div className="flex flex-col gap-2">
          <p className="text-body text-muted-foreground">{sante.quelsSignesAide}</p>
          <ChoiceGrid
            multiple
            label={sante.quelsSignes}
            value={symptoms}
            onChange={setSymptoms}
            options={(symptomList.data ?? []).map((s) => ({
              value: s.code, label: s.label_fr, icon: SYMPTOM_ICONS[s.icon ?? ''] ?? Activity,
            }))}
          />
        </div>
      )}

      {step === 'units' && (
        <div className="flex flex-col gap-2">
          <p className="text-body text-muted-foreground">{sante.quelsAnimauxAide}</p>
          <ChoiceGrid
            multiple
            label={sante.quelsAnimaux}
            value={unitIds}
            onChange={setUnitIds}
            options={(units.data ?? []).map((u) => ({
              value: u.id,
              label: u.local_name || u.label_code || u.species.label_fr,
              icon: u.kind === 'lot' ? speciesIcon(u.species.code) : PawPrint,
            }))}
          />
        </div>
      )}

      {step === 'count' && (
        <NumberStepper label={sante.combienTouches} value={affected} onChange={setCount}
                       min={Math.max(1, unitIds.length)} max={10000} />
      )}

      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        <Button icon={isLast ? Flag : ArrowRight} onClick={next} loading={sending}>
          {isLast ? mots.signaler : mots.continuer}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} onClick={back} disabled={sending}>
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
