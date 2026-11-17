/**
 * Niveau d'une alerte (charte, section 8) : 1, 2 ou 3. Le niveau 3 (rouge) n'existe
 * que si un vétérinaire habilité a validé.
 *
 * Exemple : <AlertLevelBadge level={3} />   // « Alerte validée »
 */

import { Flag, Siren, TriangleAlert, type LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'
import { niveauxAlerte } from '@/lib/vocabulaire'

export type AlertLevel = 1 | 2 | 3

const LEVELS: Record<AlertLevel, { icon: LucideIcon; classes: string }> = {
  1: { icon: Flag, classes: 'bg-health-watch text-health-watch-fg border-health-watch-line' },
  2: { icon: TriangleAlert, classes: 'bg-health-exposure text-health-exposure-fg border-health-exposure-line' },
  3: { icon: Siren, classes: 'bg-health-alert text-health-alert-fg border-health-alert-line' },
}

export function AlertLevelBadge({ level, className }: { level: AlertLevel; className?: string }) {
  const { icon: Icon, classes } = LEVELS[level]
  return (
    <span
      className={cn(
        'inline-flex min-h-8 items-center gap-1.5 rounded-full border-2 px-3 text-caption font-bold whitespace-nowrap',
        classes,
        className,
      )}
    >
      <Icon aria-hidden className="size-icon-badge" strokeWidth={2.25} />
      <span>
        {level} · {niveauxAlerte[level]}
      </span>
    </span>
  )
}
