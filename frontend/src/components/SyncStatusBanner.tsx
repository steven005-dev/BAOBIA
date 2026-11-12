import { Clock, CloudCheck, TriangleAlert, WifiOff } from 'lucide-react'
import type { OperationStatus } from '../features/offline/types'

interface SyncStatusBannerProps {
  status?: OperationStatus
  isOffline?: boolean
  className?: string
}

export function SyncStatusBanner({
  status,
  isOffline = false,
  className = '',
}: SyncStatusBannerProps) {
  if (isOffline) {
    return (
      <div
        role="status"
        className={`flex items-center gap-2 p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-secondary)] text-[var(--text-secondary)] text-sm font-bold ${className}`}
      >
        <WifiOff className="w-5 h-5 flex-shrink-0" />
        <span>Hors ligne — données gardées sur ce téléphone</span>
      </div>
    )
  }

  if (!status) return null

  switch (status) {
    case 'pending':
    case 'sending':
      return (
        <div
          role="status"
          className={`flex items-center gap-2 p-3 rounded-lg bg-[var(--warning-bg)] text-[var(--warning)] border border-[#E5C385] text-sm font-bold ${className}`}
        >
          <Clock className="w-5 h-5 flex-shrink-0" />
          <span>En attente d'envoi</span>
        </div>
      )
    case 'sent':
      return (
        <div
          role="status"
          className={`flex items-center gap-2 p-3 rounded-lg bg-[var(--success-bg)] text-[var(--success)] border border-[#B3DCBC] text-sm font-bold ${className}`}
        >
          <CloudCheck className="w-5 h-5 flex-shrink-0" />
          <span>Envoyé au serveur</span>
        </div>
      )
    case 'needs_check':
    case 'failed':
      return (
        <div
          role="status"
          className={`flex items-center gap-2 p-3 rounded-lg bg-[var(--error-bg)] text-[var(--error)] border border-[#E8BACB] text-sm font-bold ${className}`}
        >
          <TriangleAlert className="w-5 h-5 flex-shrink-0" />
          <span>À vérifier — vérification requise</span>
        </div>
      )
    default:
      return null
  }
}
