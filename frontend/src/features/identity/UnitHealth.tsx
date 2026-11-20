/**
 * Partie « Santé » de la fiche d'un animal ou d'un lot : ses signalements, du plus récent
 * au plus ancien (lecture de l'API santé de Yéo : GET /api/health-reports/?unit_id=).
 * Mots neutres : on montre où en est le signalement, jamais un diagnostic.
 */

import { Flag, HeartPulse } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { Loader } from '@/components/Loader'
import { api } from '@/lib/api'
import { etatsSignalement, messages, mots, typesSignalement } from '@/lib/vocabulaire'

import { useResource } from './useResource'

interface UnitReport {
  id: string
  report_kind: keyof typeof typesSignalement
  status: keyof typeof etatsSignalement
  occurred_at: string
  affected_count: number
}

function day(iso: string) {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function UnitHealth({ unitId }: { unitId: string }) {
  const navigate = useNavigate()
  const reports = useResource(
    () => api.get<UnitReport[]>(`/health-reports/?unit_id=${encodeURIComponent(unitId)}`),
    `sante-${unitId}`,
  )

  return (
    <Card
      title={mots.sante}
      icon={HeartPulse}
      footer={
        <Button variant="secondary" icon={Flag} onClick={() => navigate('/sante')}>
          {mots.signaler}
        </Button>
      }
    >
      {reports.loading && <Loader />}
      {reports.error && <Banner variant="error">{reports.error.message}</Banner>}
      {reports.data && reports.data.length === 0 && (
        <p className="text-body text-muted-foreground">{messages.aucunSignalement}</p>
      )}
      {reports.data && reports.data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {reports.data.slice(0, 5).map((report) => (
            <li key={report.id} className="flex flex-col gap-1 border-b border-border pb-3 last:border-0 last:pb-0">
              <p className="text-body font-bold text-foreground">
                {typesSignalement[report.report_kind] ?? report.report_kind}
              </p>
              <p className="text-caption text-muted-foreground">
                {day(report.occurred_at)} · {etatsSignalement[report.status] ?? report.status}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
