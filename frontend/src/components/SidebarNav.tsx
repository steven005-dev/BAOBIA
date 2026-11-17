/**
 * Navigation latérale sur ordinateur (charte : SidebarNavigation, 240 px). Mêmes
 * entrées, icônes et mots que la navigation basse. Affichée par AppLayout à partir
 * de la largeur « lg ».
 *
 * Exemple : <SidebarNav items={navigation} />
 */

import { NavLink } from 'react-router'

import { cn } from '@/lib/utils'
import { APP_NAME } from '@/lib/vocabulaire'

import type { NavItem } from './BottomNav'

export function SidebarNav({ items, className }: { items: NavItem[]; className?: string }) {
  return (
    <nav aria-label="Navigation principale" className={cn('flex w-sidebar shrink-0 flex-col gap-1 border-r border-border bg-surface p-4', className)}>
      <p className="px-3 pb-4 text-subtitle font-bold text-primary">{APP_NAME}</p>
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
