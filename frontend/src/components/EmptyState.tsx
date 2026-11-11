/**
 * Écran ou liste sans contenu : grande icône (48 px), une phrase, une action possible.
 *
 * Exemple :
 *   <EmptyState icon={PawPrint} title="Aucun animal"
 *     action={<Button icon={CirclePlus}>{mots.ajouter}</Button>} />
 */

import { Inbox, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  text?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon: Icon = Inbox, title, text, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center gap-4 px-4 py-12 text-center', className)}>
      <span className="flex size-24 items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Icon aria-hidden className="size-icon-empty" strokeWidth={1.75} />
      </span>
      <h2 className="text-card-title font-bold text-foreground">{title}</h2>
      {text && <p className="max-w-mobile text-body text-muted-foreground">{text}</p>}
      {action}
    </div>
  )
}
