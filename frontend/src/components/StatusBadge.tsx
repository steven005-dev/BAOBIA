/**
 * Badge d'état sanitaire (charte : HealthStatusBadge). 5 états, chacun avec sa
 * couleur, son contour sombre, son icône et son mot.
 *
 * Exemple :
 *   <StatusBadge state="exposure" />          // « Contact possible »
 *   <StatusBadge state="normal" size="large" />
 */

import { HEALTH_STATES, type HealthState } from '@/lib/healthStates'
import { cn } from '@/lib/utils'

export interface StatusBadgeProps {
  state: HealthState
  size?: 'normal' | 'large'
  className?: string
}

export function StatusBadge({ state, size = 'normal', className }: StatusBadgeProps) {
  const { label, icon: Icon, classes } = HEALTH_STATES[state]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border-2 font-bold whitespace-nowrap',
        size === 'large' ? 'min-h-touch px-4 text-body' : 'min-h-8 px-3 text-caption',
        classes,
        className,
      )}
    >
      <Icon aria-hidden className={size === 'large' ? 'size-icon' : 'size-icon-badge'} strokeWidth={2.25} />
      <span>{label}</span>
    </span>
  )
}

/** Alias du nom de la charte (section 8). */
export const HealthStatusBadge = StatusBadge
