/**
 * Mise en page commune des écrans connectés : en-tête, bandeau hors ligne, contenu,
 * navigation basse (téléphone) ou latérale (ordinateur, à partir de « lg »).
 * Les écrans des modules s'affichent dans <Outlet />.
 * « Quitter » est dans l'en-tête : tous les profils peuvent se déconnecter (le vétérinaire
 * et l'autorité n'ont pas d'Accueil, donc pas le bouton de l'Accueil).
 * La marque du profil (couleur, icône, mot) est sous l'en-tête, et aussi en haut de la
 * barre latérale sur ordinateur : on sait toujours dans quel espace on est.
 */

import { Outlet } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { AppHeader } from '@/components/AppHeader'
import { BottomNav } from '@/components/BottomNav'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { SidebarNav } from '@/components/SidebarNav'
import { profileFor } from '@/lib/profiles'

import { navigationFor } from './navigation'

export function AppLayout() {
  const { user, logout } = useAuth()
  const items = navigationFor(user?.roles.map((role) => role.code) ?? [])
  const profile = user ? profileFor(user.roles, user.full_name) : null
  return (
    <div className="flex min-h-dvh bg-background">
      <SidebarNav items={items} profile={profile} className="sticky top-0 hidden h-dvh lg:flex" />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onLogout={() => void logout()} profile={profile} />
        <OfflineIndicator variant="banner" />
        {user?.is_simulated && <DemoDataNotice />}
        <main className="mx-auto w-full max-w-mobile flex-1 px-4 pt-6 pb-[calc(var(--nav-height)+var(--space-6)+env(safe-area-inset-bottom))] lg:max-w-form lg:px-8 lg:pb-8">
          <Outlet />
        </main>
        <BottomNav items={items} className="lg:hidden" />
      </div>
    </div>
  )
}
