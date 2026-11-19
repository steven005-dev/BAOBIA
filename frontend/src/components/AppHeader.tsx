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
  'flex h-touch shrink-0 items-center gap-1 rounded-md px-2 text-caption font-bold text-primary-foreground hover:bg-primary-hover active:bg-primary-hover'

export function AppHeader({ title, onBack, onListen, onLogout, profile, className }: AppHeaderProps) {
  return (
    <header className={cn('sticky top-0 z-40 bg-primary pt-[env(safe-area-inset-top)] text-primary-foreground', className)}>
      <div className="mx-auto flex min-h-touch-primary items-center gap-2 px-4 py-1">
        {onBack && (
          <button type="button" onClick={onBack} className={headerButton}>
            <ArrowLeft aria-hidden className="size-icon" />
            {mots.retour}
          </button>
        )}
        <p className="min-w-0 flex-1 truncate text-card-title font-bold">{title ?? APP_NAME}</p>
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
