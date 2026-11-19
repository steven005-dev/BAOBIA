/**
 * Alerte expliquée (vétérinaire, autorité) : pourquoi elle existe (AL-05).
 * Règle appliquée, élevages en contact possible avec leur chemin, élevages écartés avec
 * la raison (cas négatif, AL-06). « Contact possible » ne veut jamais dire malade.
 */

import { ArrowLeft, ArrowRight, CircleCheck, Scale, TriangleAlert, Warehouse } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'

import { AlertLevelBadge } from '@/components/AlertLevelBadge'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { Loader } from '@/components/Loader'
import { StatusBadge } from '@/components/StatusBadge'
import { healthApi, type AlertDetail } from '@/features/health/api'
import { useResource } from '@/features/identity/useResource'
import { alertesTextes, mots, raisonsExposition } from '@/lib/vocabulaire'

type Exposure = AlertDetail['exposures'][number]

function ExposureCard({ exposure }: { exposure: Exposure }) {
  const exposed = exposure.status === 'exposed'
  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 shadow-card">
      <div className="flex flex-wrap items-center gap-2">
        <Warehouse aria-hidden className="size-icon text-foreground" />
        <span className="text-card-title font-bold text-foreground">{exposure.center.name}</span>
        {exposed
          ? <StatusBadge state="exposure" />
          : <span className="inline-flex min-h-8 items-center gap-1.5 rounded-full border-2 border-success bg-success-bg px-3 text-caption font-bold text-success">
              <CircleCheck aria-hidden className="size-icon-badge" />{alertesTextes.ecarte}
            </span>}
      </div>
      <ol className="flex flex-col gap-1 text-small text-foreground">
        {exposure.path.map((step) => (
          <li key={step.step} className="flex flex-wrap items-center gap-1">
            <span className="font-bold">{step.from}</span>
            <ArrowRight aria-hidden className="size-icon-small" />
            <span className="font-bold">{step.to}</span>
            <span className="text-muted-foreground">
              · {new Date(step.occurred_at).toLocaleDateString('fr-FR')} ·{' '}
              {raisonsExposition[step.reason] ?? step.reason}
            </span>
          </li>
        ))}
      </ol>
      {exposed && (
        <p className="text-caption text-muted-foreground">
          {alertesTextes.profondeur} {exposure.depth}
        </p>
      )}
    </li>
  )
}

export function AlertDetailPage() {
  const { alertId = '' } = useParams()
  const navigate = useNavigate()
  const alert = useResource(() => healthApi.alert(alertId), alertId)

  if (alert.loading) return <Loader />
  if (alert.error) return <Banner variant="error">{alert.error.message}</Banner>
  const a = alert.data
  if (!a) return null

  const exposed = a.exposures.filter((e) => e.status === 'exposed')
  const excluded = a.exposures.filter((e) => e.status === 'excluded_negative')

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)} className="self-start">
        {mots.retour}
      </Button>
      <div className="flex flex-col gap-2">
        <AlertLevelBadge level={a.level} className="self-start" />
        <h1 className="text-title font-bold text-foreground">
          {a.disease?.label_fr ?? mots.alerte} · {a.zone.name}
        </h1>
        <p className="text-body text-muted-foreground">
          {alertesTextes.foyer} : {a.focus_center?.name ?? '—'}
          {a.validated_by && ` · ${alertesTextes.valideePar} ${a.validated_by}`}
        </p>
      </div>
      {a.is_simulated && <DemoDataNotice />}
      {a.confidence === 'reduced' && <Banner variant="warning">{alertesTextes.confianceReduite}</Banner>}

      <Card title={alertesTextes.regle} icon={Scale}>
        <p className="text-body">
          {a.rule.lookback_days} {alertesTextes.jours} · {alertesTextes.profondeur} {a.rule.max_depth} · v{a.rule.version}
        </p>
        {a.rule.experimental && (
          <p className="text-small text-muted-foreground">{alertesTextes.regleExperimentale}</p>
        )}
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="flex items-center gap-2 text-subtitle font-bold text-foreground">
          <TriangleAlert aria-hidden className="size-icon" />
          {alertesTextes.elevagesContact} ({exposed.length})
        </h2>
        <p className="text-small text-muted-foreground">{alertesTextes.pasUnDiagnostic}</p>
        {exposed.length === 0
          ? <p className="text-body">{alertesTextes.aucunContact}</p>
          : <ul className="flex flex-col gap-3">{exposed.map((e) => <ExposureCard key={e.center.id} exposure={e} />)}</ul>}
      </section>

      {excluded.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-subtitle font-bold text-foreground">
            <CircleCheck aria-hidden className="size-icon" />
            {alertesTextes.elevagesEcartes} ({excluded.length})
          </h2>
          <ul className="flex flex-col gap-3">{excluded.map((e) => <ExposureCard key={e.center.id} exposure={e} />)}</ul>
        </section>
      )}
    </div>
  )
}
