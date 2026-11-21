/**
 * Navigation latérale sur ordinateur (charte : SidebarNavigation, 240 px). Mêmes
 * entrées, icônes et mots que la navigation basse. Affichée par AppLayout à partir
 * de la largeur « lg ».
 *
 * Exemple : <SidebarNav items={navigation} profile={profile} />
 */

import { NavLink } from 'react-router'

import type { Profile } from '@/lib/profiles'
import { cn } from '@/lib/utils'
import { APP_NAME } from '@/lib/vocabulaire'

import type { NavItem } from './BottomNav'
import { ProfileChip } from './ProfileBar'

export function SidebarNav({ items, profile, className }: { items: NavItem[]; profile?: Profile | null; className?: string }) {
  return (
    <nav aria-label="Navigation principale" className={cn('flex w-sidebar shrink-0 flex-col gap-1 bg-brand-gradient p-4 text-primary-foreground', className)}>
      <p className="flex items-center gap-3 px-2 pt-1 pb-5 font-display text-subtitle font-bold tracking-wide">
        <img src="/baobia-icon.svg" alt="" className="size-10 rounded-md ring-1 ring-on-brand-line" />
        {APP_NAME}
      </p>
      {profile && <ProfileChip profile={profile} className="mb-5" />}
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex min-h-touch items-center gap-3 rounded-md border-l-4 px-3 font-display text-body transition-colors',
              isActive ? 'border-brand-mint bg-on-brand-soft font-bold text-primary-foreground' : 'border-transparent text-on-brand-muted hover:bg-on-brand-soft hover:text-primary-foreground',
            )
          }
        >
          <Icon aria-hidden className="size-icon shrink-0" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
