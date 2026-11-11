/**
 * Carte : surface blanche, rayon 16 px, ombre légère. Titre (20 px) facultatif avec icône.
 *
 * Exemple :
 *   <Card title="Élevage A" icon={Warehouse} footer={<Button>...</Button>}>
 *     12 animaux
 *   </Card>
 */

import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface CardProps {
  title?: string
  icon?: LucideIcon
  /** Élément à droite du titre (ex. StatusBadge). */
  aside?: ReactNode
  footer?: ReactNode
  children?: ReactNode
  className?: string
}

export function Card({ title, icon: Icon, aside, footer, children, className }: CardProps) {
  return (
    <section className={cn('flex flex-col gap-3 rounded-lg border border-border bg-card p-4 text-card-foreground shadow-card', className)}>
      {(title || aside) && (
        <header className="flex flex-wrap items-center justify-between gap-2">
          {title && (
            <h3 className="flex items-center gap-2 text-card-title font-bold">
              {Icon && <Icon aria-hidden className="size-icon shrink-0 text-primary" />}
              {title}
            </h3>
          )}
          {aside}
        </header>
      )}
      {children && <div className="text-body">{children}</div>}
      {footer && <footer className="flex flex-col gap-3">{footer}</footer>}
    </section>
  )
}
