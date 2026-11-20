/**
 * Alertes.
 * - Vétérinaire, autorité : les alertes de sa zone (niveau, maladie, élevages en contact).
 * - Éleveur, agent : uniquement ses messages neutres (RG-13) ; jamais d'alerte détaillée,
 *   jamais l'élevage d'origine.
 */

import { ChevronRight, Siren, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { AlertLevelBadge } from '@/components/AlertLevelBadge'
import { Banner } from '@/components/Banner'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { healthApi, type AlertSummary } from '@/features/health/api'
import { useResource } from '@/features/identity/useResource'
import { notificationsApi } from '@/features/notifications/api'
import { alertesTextes, mots, textesNotifications } from '@/lib/vocabulaire'

function AlertRow({ alert }: { alert: AlertSummary }) {
  return (
    <li>
      <Link to={`/alertes/${alert.id}`}
            className="flex min-h-touch items-center gap-3 rounded-lg border border-border bg-surface p-4 shadow-card">
        <div className="flex flex-1 flex-col gap-2">
          <AlertLevelBadge level={alert.level} className="self-start" />
          <span className="text-card-title font-bold text-foreground">
            {alert.disease?.label_fr ?? mots.alerte} · {alert.zone.name}
          </span>
          <span className="text-small text-muted-foreground">
            {alertesTextes.elevagesContact} : {alert.exposed_count} · {alertesTextes.ouverteLe}{' '}
            {new Date(alert.opened_at).toLocaleDateString('fr-FR')}
          </span>
        </div>
        <ChevronRight aria-hidden className="size-icon text-muted-foreground" />
      </Link>
    </li>
  )
}

function ProfessionalAlerts() {
  const alerts = useResource(healthApi.alerts, 'alertes')
  if (alerts.loading) return <Loader />
  if (alerts.error) return <Banner variant="error">{alerts.error.message}</Banner>
  const items = alerts.data ?? []
  return (
    <>
      {items.some((a) => a.is_simulated) && <DemoDataNotice />}
      {items.length === 0
        ? <EmptyState icon={Siren} title={alertesTextes.aucuneAlerte} text={alertesTextes.aucuneAlerteAide} />
        : <ul className="flex flex-col gap-3">{items.map((a) => <AlertRow key={a.id} alert={a} />)}</ul>}
    </>
  )
}

function BreederMessages() {
  const list = useResource(notificationsApi.list, 'messages')
  if (list.loading) return <Loader />
  if (list.error) return <Banner variant="error">{list.error.message}</Banner>
  const items = list.data ?? []
  if (items.length === 0) return <EmptyState icon={Siren} title={alertesTextes.aucunMessage} />
  return (
    <ul className="flex flex-col gap-3">
      {items.map((n) => (
        <li key={n.id}>
          <Banner variant="warning" title={new Date(n.created_at).toLocaleDateString('fr-FR')}>
            <span className="inline-flex items-start gap-2">
              <TriangleAlert aria-hidden className="size-icon shrink-0" />
              {textesNotifications[n.message_code] ?? n.message_code}
            </span>
          </Banner>
        </li>
      ))}
    </ul>
  )
}

export function AlertsPage() {
  const { hasRole } = useAuth()
  const professional = hasRole('veterinarian') || hasRole('authority')
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">
        {professional ? mots.alertes : alertesTextes.mesMessages}
      </h1>
      {professional ? <ProfessionalAlerts /> : <BreederMessages />}
    </div>
  )
}
