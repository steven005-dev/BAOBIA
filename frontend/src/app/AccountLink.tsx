/**
 * « Mon compte » dans l'en-tête, sur téléphone seulement : la navigation du bas garde
 * 4 entrées au plus (charte, principe 9). Sur ordinateur, il est en bas de la barre latérale.
 */

import { UserRound } from 'lucide-react'
import { NavLink } from 'react-router'

import { cn } from '@/lib/utils'
import { profilTextes } from '@/lib/vocabulaire'

export function AccountLink() {
  return (
    <NavLink to="/profil" aria-label={profilTextes.titre}
             className={({ isActive }) => cn(
               'flex h-touch shrink-0 items-center gap-1.5 rounded-full px-2 text-caption font-bold text-primary-foreground hover:bg-on-brand-soft sm:px-3 lg:hidden',
               isActive && 'bg-on-brand-soft',
             )}>
      <UserRound aria-hidden className="size-icon" />
      <span className="hidden sm:inline">{profilTextes.ongletCourt}</span>
    </NavLink>
  )
}
