import { useSyncExternalStore } from 'react'

import { getPendingCount, subscribePending } from '@/offline'

/** Nombre d'actions en attente d'envoi (file hors ligne). */
export function usePendingCount(): number {
  return useSyncExternalStore(subscribePending, getPendingCount, () => 0)
}
