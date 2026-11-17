/**
 * État du réseau et des envois, toujours visible (charte, section 10).
 * - variant="pill" (dans l'en-tête) : « En ligne », « Hors ligne », « 3 en attente ».
 * - variant="banner" (sous l'en-tête) : s'affiche seulement hors ligne ou s'il reste
 *   des envois, avec la phrase de la charte.
 * Par défaut, lit le réseau du téléphone et la file d'envoi (src/offline). Les props
 * `online` et `pending` servent à forcer un état (page /composants, tests).
 *
 * Exemple : <OfflineIndicator />   <OfflineIndicator variant="banner" />
 */

import { Clock, Wifi, WifiOff } from 'lucide-react'

import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import { usePendingCount } from '@/hooks/usePendingCount'
import { cn } from '@/lib/utils'
import { messages, mots } from '@/lib/vocabulaire'

export interface OfflineIndicatorProps {
  variant?: 'pill' | 'banner'
  online?: boolean
  pending?: number
  className?: string
}

export function OfflineIndicator({ variant = 'pill', online, pending, className }: OfflineIndicatorProps) {
  const networkOnline = useOnlineStatus()
  const queued = usePendingCount()
  const isOnline = online ?? networkOnline
  const count = pending ?? queued
  const pendingText = count > 0 ? `${count} ${mots.enAttente.toLowerCase()}` : null

  if (variant === 'banner') {
    if (isOnline && count === 0) return null
    return (
      <div
        role="status"
        className={cn(
          'flex items-start gap-3 border-b-2 border-warning bg-warning-bg px-4 py-3 text-body font-bold text-warning',
          className,
        )}
      >
        {isOnline ? <Clock aria-hidden className="mt-0.5 size-icon shrink-0" /> : <WifiOff aria-hidden className="mt-0.5 size-icon shrink-0" />}
        <p>
          {isOnline ? messages.enAttente : messages.horsConnexion}
          {pendingText && <span className="block text-small">{pendingText}</span>}
        </p>
      </div>
    )
  }

  const Icon = isOnline ? (count > 0 ? Clock : Wifi) : WifiOff
  return (
    <span
      role="status"
      className={cn(
        'inline-flex min-h-touch items-center gap-1.5 rounded-full border-2 px-3 text-caption font-bold whitespace-nowrap',
        isOnline && count === 0
          ? 'border-success bg-success-bg text-success'
          : 'border-warning bg-warning-bg text-warning',
        className,
      )}
    >
      <Icon aria-hidden className="size-icon-badge shrink-0" />
      <span>{isOnline ? (pendingText ?? mots.enLigne) : mots.horsLigne}</span>
      {!isOnline && pendingText && <span>· {pendingText}</span>}
    </span>
  )
}

/** Noms de la charte (section 8). */
export const SyncStatusBanner = (props: Omit<OfflineIndicatorProps, 'variant'>) => (
  <OfflineIndicator {...props} variant="banner" />
)
