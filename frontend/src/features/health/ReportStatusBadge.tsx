/**
 * État d'un signalement (SA-04) : icône + mot. Couleurs neutres et fonctionnelles :
 * le jaune, l'orange et le rouge sanitaires sont réservés aux états sanitaires.
 */

import { CircleCheck, CircleX, Clock, Inbox, Stethoscope, type LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'
import { etatsSignalement } from '@/lib/vocabulaire'

import type { ReportStatus } from './api'

const STYLES: Record<ReportStatus, { icon: LucideIcon; classes: string }> = {
  submitted: { icon: Inbox, classes: 'border-info bg-info-bg text-info' },
  under_review: { icon: Stethoscope, classes: 'border-info bg-info-bg text-info' },
  validated: { icon: CircleCheck, classes: 'border-success bg-success-bg text-success' },
  rejected: { icon: CircleX, classes: 'border-border bg-muted text-muted-foreground' },
  closed: { icon: Clock, classes: 'border-border bg-muted text-muted-foreground' },
}

export function ReportStatusBadge({ status, className }: { status: ReportStatus; className?: string }) {
  const { icon: Icon, classes } = STYLES[status]
  return (
    <span className={cn(
      'inline-flex min-h-8 items-center gap-1.5 rounded-full border-2 px-3 text-caption font-bold whitespace-nowrap',
      classes, className,
    )}>
      <Icon aria-hidden className="size-icon-badge" strokeWidth={2.25} />
      <span>{etatsSignalement[status]}</span>
    </span>
  )
}
