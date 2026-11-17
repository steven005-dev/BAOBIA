/**
 * Navigation basse du téléphone (charte, section 7) : 4 entrées au plus, toujours
 * visibles, icône + mot. L'entrée active a un trait en haut, un fond clair, le mot
 * en gras et aria-current (pas seulement une couleur). `emphasis` met une entrée en
 * valeur au centre (Scanner).
 *
 * Exemple :
 *   <BottomNav items={[{ to: '/', label: mots.accueil, icon: House, end: true }, ...]} />
 */

import type { LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router'

import { cn } from '@/lib/utils'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Actif seulement sur ce chemin exact (pour "/"). */
  end?: boolean
  emphasis?: boolean
}

export function BottomNav({ items, className }: { items: NavItem[]; className?: string }) {
  if (import.meta.env.DEV && items.length > 4) {
    console.warn('BottomNav : 4 entrées au plus (charte, principe 9).')
  }
  return (
    <nav
      aria-label="Navigation principale"
      className={cn(
        'fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]',
        className,
      )}
    >
      <ul className="mx-auto flex h-nav max-w-mobile items-stretch">
        {items.slice(0, 4).map(({ to, label, icon: Icon, end, emphasis }) => (
          <li key={to} className="flex flex-1">
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'relative flex flex-1 flex-col items-center justify-center gap-1 text-caption',
                  isActive ? 'bg-accent font-bold text-primary' : 'text-muted-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && <span aria-hidden className="absolute inset-x-3 top-0 h-1 rounded-b-sm bg-primary" />}
                  <span
                    className={cn(
                      'flex size-10 items-center justify-center rounded-full',
                      emphasis && 'bg-primary text-primary-foreground',
                    )}
                  >
                    <Icon aria-hidden className="size-icon" strokeWidth={isActive ? 2.5 : 2} />
                  </span>
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
