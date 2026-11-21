/**
 * En-tête de chaque écran (charte, section 4) : marque ou titre, état du réseau, et la
 * place réservée à l'aide audio. Bouton Retour facultatif.
 *
 * Exemple :
 *   <AppHeader />                                  // marque BAOBIA
 *   <AppHeader title="Élevage A" onBack={() => navigate(-1)} onListen={lireLaPage} />
 *   <AppHeader onLogout={logout} />                // bouton Quitter, pour tous les profils
 *   <AppHeader profile={profile} />                // bandeau du profil sous l'en-tête
 */

import { ArrowLeft, LogOut, Volume2 } from 'lucide-react'

import type { Profile } from '@/lib/profiles'
import { cn } from '@/lib/utils'
import { APP_NAME, mots } from '@/lib/vocabulaire'

import { OfflineIndicator } from './OfflineIndicator'
import { ProfileBar } from './ProfileBar'

export interface AppHeaderProps {
  title?: string
  onBack?: () => void
  /** Aide audio : bouton « Écouter » affiché seulement quand elle est disponible. */
  onListen?: () => void
  /** Se déconnecter : bouton « Quitter » (icône et mot), visible sur tous les écrans. */
  onLogout?: () => void
  /** Profil connecté : bandeau couleur, icône et mot, sur tous les écrans. */
  profile?: Profile | null
  className?: string
}

const headerButton =
  'flex h-touch shrink-0 items-center gap-1.5 rounded-full px-3 text-caption font-bold text-primary-foreground hover:bg-on-brand-soft active:bg-on-brand-soft'

export function AppHeader({ title, onBack, onListen, onLogout, profile, className }: AppHeaderProps) {
  return (
    <header className={cn('sticky top-0 z-40 bg-brand-gradient pt-[env(safe-area-inset-top)] text-primary-foreground shadow-card', className)}>
      <div className="mx-auto flex min-h-touch-primary items-center gap-2 px-4 py-1">
        {onBack && (
          <button type="button" onClick={onBack} className={headerButton}>
            <ArrowLeft aria-hidden className="size-icon" />
            {mots.retour}
          </button>
        )}
        <p className="flex min-w-0 flex-1 items-center gap-2.5 truncate font-display text-card-title font-bold tracking-wide">
          {/* Sans titre : le logo (le nom aussi dès qu'il y a la place) ; sur ordinateur, la barre latérale l'a déjà. */}
          {!title && <img src="/baobia-icon.svg" alt={APP_NAME} className="size-9 shrink-0 rounded-md ring-1 ring-on-brand-line lg:hidden" />}
          <span className={title ? 'truncate' : 'hidden truncate sm:inline lg:hidden'}>{title ?? APP_NAME}</span>
        </p>
        <OfflineIndicator />
        {/* Place de l'aide audio (charte, principe 10) : réservée même vide. */}
        <div className="flex min-w-touch justify-end">
          {onListen && (
            <button type="button" onClick={onListen} className={headerButton}>
              <Volume2 aria-hidden className="size-icon" />
              {mots.ecouter}
            </button>
          )}
        </div>
        {onLogout && (
          <button type="button" onClick={onLogout} className={headerButton}>
            <LogOut aria-hidden className="size-icon" />
            {mots.quitter}
          </button>
        )}
      </div>
      {profile && <ProfileBar profile={profile} />}
    </header>
  )
}
