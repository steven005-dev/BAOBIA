/**
 * Marque de l'espace de l'utilisateur, sous l'en-tête : couleur, icône et mot du profil,
 * puis nom et zone. Style clair (fond clair, texte et filet de la couleur du profil) pour
 * se détacher de l'en-tête vert foncé, même en plein soleil. Sert à savoir d'un coup d'œil « je suis dans l'espace vétérinaire ».
 * ProfileChip : même marque en pastille (barre latérale sur ordinateur).
 *
 * Exemple : <ProfileBar profile={{ role: 'veterinarian', name: 'Awa Koné', zone: 'Zone Nord' }} />
 */

import { cn } from '@/lib/utils'
import { type Profile, profileStyles } from '@/lib/profiles'

export function ProfileBar({ profile, className }: { profile: Profile; className?: string }) {
  const { label, icon: Icon, soft } = profileStyles[profile.role]
  const details = [profile.name, profile.zone].filter(Boolean).join(' · ')
  return (
    <div className={cn('flex min-h-8 items-center gap-2 border-b-2 px-4 py-0.5 text-small', soft, className)}>
      <Icon aria-hidden className="size-icon-small shrink-0" />
      <span className="font-bold">{label}</span>
      {details && <span className="min-w-0 truncate">· {details}</span>}
    </div>
  )
}

export function ProfileChip({ profile, className }: { profile: Profile; className?: string }) {
  const { label, icon: Icon, soft } = profileStyles[profile.role]
  return (
    <div className={cn('flex flex-col gap-0.5 rounded-md border-l-4 px-3 py-2', soft, className)}>
      <span className="flex items-center gap-2 text-small font-bold">
        <Icon aria-hidden className="size-icon-small shrink-0" />
        {label}
      </span>
      {profile.zone && <span className="text-caption">{profile.zone}</span>}
    </div>
  )
}
