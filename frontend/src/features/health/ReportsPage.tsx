/**
 * Signalements (gabarit Liste).
 * - Éleveur, agent : ses signalements et leur état (SA-04), bouton Signaler.
 * - Vétérinaire, autorité : les signalements de sa zone, ceux à examiner d'abord.
 */

import { ChevronRight, Flag } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { useResource } from '@/features/identity/useResource'
import { mots, sante, typesSignalement } from '@/lib/vocabulaire'

import { healthApi, type Report } from './api'
import { ReportStatusBadge } from './ReportStatusBadge'

const TO_REVIEW = ['submitted', 'under_review']

function ReportRow({ report }: { report: Report }) {
  return (
    <li>
      <Link
        to={`/sante/${report.id}`}
        className="flex min-h-touch items-center gap-3 rounded-lg border border-border bg-surface p-4 shadow-card"
      >
        <div className="flex flex-1 flex-col gap-1">
          <span className="text-card-title font-bold text-foreground">
            {typesSignalement[report.report_kind]}
          </span>
          <span className="text-small text-muted-foreground">
            {report.center.name} · {new Date(report.occurred_at).toLocaleDateString('fr-FR')}
            {' · '}{sante.morts} {report.dead_count} · {sante.malades} {report.affected_count - report.dead_count}
          </span>
          <ReportStatusBadge status={report.status} className="self-start" />
        </div>
        <ChevronRight aria-hidden className="size-icon text-muted-foreground" />
      </Link>
    </li>
  )
}

export function ReportsPage() {
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const professional = hasRole('veterinarian') || hasRole('authority')
  const reports = useResource(healthApi.reports, 'signalements')

  if (reports.loading) return <Loader />
  if (reports.error) return <Banner variant="error">{reports.error.message}</Banner>

  const all = reports.data ?? []
  const toReview = professional ? all.filter((r) => TO_REVIEW.includes(r.status)) : []
  const others = professional ? all.filter((r) => !TO_REVIEW.includes(r.status)) : all

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">
        {professional ? mots.signalements : sante.mesSignalements}
      </h1>
      {!professional && (
        <Button icon={Flag} onClick={() => navigate('/sante/signaler')}>{mots.signaler}</Button>
      )}
      {all.some((r) => r.is_simulated) && <DemoDataNotice />}
      {all.length === 0 && (
        <EmptyState icon={Flag} title={sante.aucunSignalement}
                    text={professional ? undefined : sante.aucunSignalementAide} />
      )}
      {toReview.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-subtitle font-bold text-foreground">{sante.aExaminer}</h2>
          <ul className="flex flex-col gap-3">
            {toReview.map((r) => <ReportRow key={r.id} report={r} />)}
          </ul>
        </section>
      )}
      {others.length > 0 && (
        <ul className="flex flex-col gap-3">
          {others.map((r) => <ReportRow key={r.id} report={r} />)}
        </ul>
      )}
    </div>
  )
}
