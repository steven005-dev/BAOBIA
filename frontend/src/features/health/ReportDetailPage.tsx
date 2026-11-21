/**
 * Fiche d'un signalement (gabarit Fiche détail).
 * - Éleveur : ce qu'il a signalé et l'état (reçu, en examen, validé, refusé).
 * - Vétérinaire habilité de la zone : décisions passées et décision à prendre (en ligne).
 *   Valider (niveau 3) exige la maladie retenue ; Refuser exige un motif.
 * Seul un vétérinaire habilité valide (RG-08) : le serveur le vérifie de toute façon.
 */

import { ArrowLeft, CircleX, CircleHelp, FlaskConical, ShieldCheck, Siren, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { useToast } from '@/components/Toast'
import { useResource } from '@/features/identity/useResource'
import { ApiError } from '@/lib/api'
import {
  decisionsVeterinaire, erreurs, messages, mots, pistesTextes, sante, typesSignalement,
} from '@/lib/vocabulaire'

import { healthApi, type Decision } from './api'
import { DiseaseLeads } from './DiseaseLeads'
import { ReportStatusBadge } from './ReportStatusBadge'

const DECISIONS: { value: Decision; icon: typeof ShieldCheck }[] = [
  { value: 'validate_level3', icon: ShieldCheck },
  { value: 'raise_level2', icon: TriangleAlert },
  { value: 'request_info', icon: CircleHelp },
  { value: 'dismiss', icon: CircleX },
]

function VetDecision({ reportId, species, onDone }: {
  reportId: string; species?: string; onDone: () => void
}) {
  const toast = useToast()
  const diseases = useResource(() => healthApi.diseases(species), `maladies-${species ?? ''}`)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [disease, setDisease] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Décisions lourdes (valider niveau 3, refuser) : confirmées avant l'envoi.
  const [confirming, setConfirming] = useState(false)
  const heavy = decision === 'validate_level3' || decision === 'dismiss'

  const needsDisease = decision === 'validate_level3' || decision === 'raise_level2'
  const ready = () => {
    if (!decision || (decision === 'validate_level3' && !disease) ||
        (decision === 'dismiss' && !note.trim())) {
      setError(messages.champManquant)
      return false
    }
    return true
  }

  const ask = () => {
    if (!ready()) return
    if (heavy) setConfirming(true)
    else void send()
  }

  const send = async () => {
    if (!ready() || !decision) return
    setConfirming(false)
    setSending(true)
    setError(null)
    try {
      await healthApi.review(reportId, decision, needsDisease ? disease ?? undefined : undefined, note)
      toast.show(sante.decisionEnregistree, 'success')
      onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  return (
    <Card title={sante.decisionVeterinaire} icon={ShieldCheck}>
      <div className="flex flex-col gap-4">
        <ChoiceGrid
          label={sante.decisionVeterinaire}
          value={decision}
          onChange={(value) => setDecision(value as Decision)}
          options={DECISIONS.map((d) => ({ value: d.value, label: decisionsVeterinaire[d.value], icon: d.icon }))}
        />
        {needsDisease && (
          <ChoiceGrid
            label={sante.maladieRetenue}
            value={disease}
            onChange={setDisease}
            options={(diseases.data ?? []).map((d) => ({ value: d.code, label: d.label_fr, icon: Siren }))}
          />
        )}
        <Field label={sante.motif} help={decision === 'dismiss' ? sante.motifAide : undefined}>
          <Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </Field>
        {error && <Banner variant="error">{error}</Banner>}
        <Button icon={ShieldCheck} onClick={ask} loading={sending}>
          {decision === 'dismiss' ? mots.refuser : mots.valider}
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        title={decision === 'dismiss' ? sante.confirmerRefusTitre : sante.confirmerValidationTitre}
        confirmLabel={decision === 'dismiss' ? mots.refuser : mots.valider}
        confirmIcon={decision === 'dismiss' ? CircleX : ShieldCheck}
        variant={decision === 'dismiss' ? 'danger' : 'primary'}
        loading={sending}
        onConfirm={() => void send()}
        onCancel={() => setConfirming(false)}
      >
        {decision === 'dismiss'
          ? sante.confirmerRefusTexte
          : <>
              <strong>{(diseases.data ?? []).find((d) => d.code === disease)?.label_fr}</strong>
              {' · '}{sante.confirmerValidationTexte}
            </>}
      </ConfirmDialog>
    </Card>
  )
}

export function ReportDetailPage() {
  const { reportId = '' } = useParams()
  const navigate = useNavigate()
  const { hasRole, user } = useAuth()
  const report = useResource(() => healthApi.report(reportId), reportId)

  if (report.loading) return <Loader />
  if (report.error) return <Banner variant="error">{report.error.message}</Banner>
  const r = report.data
  if (!r) return null

  const canDecide = hasRole('veterinarian') && user?.has_valid_habilitation &&
    r.reviews !== undefined && !['closed'].includes(r.status)
  const species = r.subjects[0]?.species_code

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)} className="self-start">
        {mots.retour}
      </Button>
      <div className="flex flex-col gap-2">
        <h1 className="text-title font-bold text-foreground">{typesSignalement[r.report_kind]}</h1>
        <ReportStatusBadge status={r.status} className="self-start" />
      </div>
      {!user?.is_simulated && r.is_simulated && <DemoDataNotice />}

      <Card>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-body">
          <dt className="font-bold">{mots.elevage}</dt><dd>{r.center.name}</dd>
          <dt className="font-bold">{sante.signaleLe}</dt>
          <dd>{new Date(r.occurred_at).toLocaleString('fr-FR')}</dd>
          <dt className="font-bold">{sante.morts}</dt><dd>{r.dead_count}</dd>
          <dt className="font-bold">{sante.malades}</dt><dd>{r.affected_count - r.dead_count}</dd>
          <dt className="font-bold">{mots.symptomes}</dt>
          <dd>{r.symptoms.map((s) => s.label_fr).join(', ') || '—'}</dd>
        </dl>
      </Card>

      {r.leads && <DiseaseLeads leads={r.leads} />}
      {r.leads && (
        <Button variant="secondary" icon={FlaskConical} onClick={() => navigate(`/sante/${r.id}/laboratoire`)}>
          {pistesTextes.ficheLabo}
        </Button>
      )}

      {r.reviews && r.reviews.length > 0 && (
        <Card title={mots.historique}>
          <ul className="flex flex-col gap-2 text-body">
            {r.reviews.map((review) => (
              <li key={review.id}>
                <strong>{decisionsVeterinaire[review.decision]}</strong>
                {review.disease && ` · ${review.disease.label_fr}`} · {review.vet_name} ·{' '}
                {new Date(review.occurred_at).toLocaleString('fr-FR')}
                {review.note && <p className="text-small text-muted-foreground">{review.note}</p>}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {canDecide && <VetDecision reportId={r.id} species={species} onDone={report.reload} />}
    </div>
  )
}
