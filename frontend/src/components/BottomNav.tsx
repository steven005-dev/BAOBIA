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
        'fixed inset-x-0 bottom-0 z-40 rounded-t-xl border-t border-border/60 bg-surface/95 pb-[env(safe-area-inset-bottom)] shadow-raised backdrop-blur',
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
                  'relative flex flex-1 flex-col items-center justify-center gap-1 font-display text-caption',
                  isActive ? 'font-bold text-primary' : 'text-muted-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn(
                      'flex h-9 w-14 items-center justify-center rounded-full transition-colors',
                      isActive && !emphasis && 'bg-accent',
                      emphasis && 'size-12 -mt-5 bg-brand-gradient text-primary-foreground shadow-raised ring-4 ring-surface',
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
