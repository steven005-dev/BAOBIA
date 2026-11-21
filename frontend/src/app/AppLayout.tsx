/**
 * Mise en page commune des écrans connectés : en-tête, bandeau hors ligne, contenu,
 * navigation basse (téléphone) ou latérale (ordinateur, à partir de « lg »).
 * Les écrans des modules s'affichent dans <Outlet />.
 * Se déconnecter : « Déconnexion » dans l'onglet « Mon compte » (dernier onglet, tous les
 * profils) ; plus de bouton dans l'en-tête.
 * La marque du profil (couleur, icône, mot) est sous l'en-tête sur téléphone, et en haut de
 * la barre latérale sur ordinateur : on sait toujours dans quel espace on est.
 */

import { Outlet, useLocation } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { AppHeader } from '@/components/AppHeader'
import { BottomNav } from '@/components/BottomNav'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { SidebarNav } from '@/components/SidebarNav'
import { healthApi } from '@/features/health/api'
import { useLiveResource } from '@/features/health/live'
import { NotificationBell } from '@/features/notifications/NotificationBell'
import { profileFor } from '@/lib/profiles'

import { navigationFor } from './navigation'

const TO_REVIEW = ['submitted', 'under_review']
const OPEN = ['open', 'monitoring']

/** Vétérinaire, autorité : signalements à examiner et alertes ouvertes, mis à jour tout seuls
 *  (pastilles de la navigation). Rien n'est chargé pour les autres profils. */
function useDeskCounts(desk: boolean) {
  const reports = useLiveResource(() => (desk ? healthApi.reports() : Promise.resolve([])),
                                  desk ? 'compte-signalements' : 'aucun', 30000)
  const alerts = useLiveResource(() => (desk ? healthApi.alerts() : Promise.resolve([])),
                                 desk ? 'compte-alertes' : 'aucun', 30000)
  return {
    toReview: reports.data?.filter((r) => TO_REVIEW.includes(r.status)).length,
    openAlerts: alerts.data?.filter((a) => OPEN.includes(a.status)).length,
  }
}

export function AppLayout() {
  const { user } = useAuth()
  const items = navigationFor(user?.roles.map((role) => role.code) ?? [])
  const profile = user ? profileFor(user.roles, user.full_name) : null
  // Vétérinaire et autorité travaillent surtout sur ordinateur : écran plus large (carte, listes).
  const desk = profile?.role === 'veterinarian' || profile?.role === 'authority'
  const counts = useDeskCounts(desk)
  const withBadges = items.map((item) => ({
    ...item,
    badge: item.to === '/sante' ? counts.toReview : item.to === '/alertes' ? counts.openAlerts : undefined,
  }))
  const { pathname } = useLocation()
  const current = [...items].sort((a, b) => b.to.length - a.to.length)
    .find((item) => (item.end ? pathname === item.to : pathname.startsWith(item.to)))
  return (
    <div className="flex min-h-dvh bg-background">
      <SidebarNav items={withBadges} profile={profile} className="sticky top-0 hidden h-dvh lg:flex" />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader profile={profile} desktopTitle={current?.label} extra={<NotificationBell />} />
        <OfflineIndicator variant="banner" />
        {user?.is_simulated && <DemoDataNotice />}
        <main className={`mx-auto w-full max-w-mobile flex-1 px-4 pt-6 pb-[calc(var(--nav-height)+var(--space-6)+env(safe-area-inset-bottom))] lg:px-8 lg:pb-8 ${desk ? 'lg:max-w-6xl' : 'lg:max-w-form'}`}>
          <Outlet />
        </main>
        <BottomNav items={withBadges} className="lg:hidden" />
      </div>
    </div>
  )
}
