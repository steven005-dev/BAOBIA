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
    <nav aria-label="Navigation principale" className={cn('flex w-sidebar shrink-0 flex-col gap-1 border-r border-border bg-surface p-4', className)}>
      <p className="px-3 pb-2 text-subtitle font-bold text-primary">{APP_NAME}</p>
      {profile && <ProfileChip profile={profile} className="mb-4" />}
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex min-h-touch items-center gap-3 rounded-md border-l-4 px-3 text-body',
              isActive ? 'border-primary bg-accent font-bold text-primary' : 'border-transparent text-foreground hover:bg-muted',
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
