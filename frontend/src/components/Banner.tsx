/**
 * Message encadré : succès, erreur, information, avertissement (charte, couleurs
 * fonctionnelles). Toujours icône + texte. Les erreurs sont annoncées tout de suite
 * aux lecteurs d'écran (role="alert").
 *
 * Exemple :
 *   <Banner variant="error">{erreurs.reseau}</Banner>
 *   <Banner variant="success" title={messages.transfertEnvoye} />
 */

import { CircleCheck, CircleX, Info, TriangleAlert, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type BannerVariant = 'success' | 'error' | 'info' | 'warning'

const VARIANTS: Record<BannerVariant, { icon: LucideIcon; classes: string }> = {
  success: { icon: CircleCheck, classes: 'border-success bg-success-bg text-success' },
  error: { icon: CircleX, classes: 'border-error bg-error-bg text-error' },
  info: { icon: Info, classes: 'border-info bg-info-bg text-info' },
  warning: { icon: TriangleAlert, classes: 'border-warning bg-warning-bg text-warning' },
}

export interface BannerProps {
  variant?: BannerVariant
  title?: string
  children?: ReactNode
  /** Action proposée (ex. bouton Réessayer). */
  action?: ReactNode
  className?: string
}

export function Banner({ variant = 'info', title, children, action, className }: BannerProps) {
  const { icon: Icon, classes } = VARIANTS[variant]
  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-md border-2 p-4', classes, className)}
    >
      <Icon aria-hidden className="mt-0.5 size-icon shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {title && <p className="text-body font-bold">{title}</p>}
        {children && <div className={cn('text-body', title ? '' : 'font-bold')}>{children}</div>}
        {action}
      </div>
    </div>
  )
}
