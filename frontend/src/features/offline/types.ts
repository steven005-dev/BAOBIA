import type { Operation } from '@/offline'

export type StoredOperationStatus = 'pending' | 'sending' | 'sent' | 'check'

export interface QueuedOperation extends Operation {
  id: string
  status: StoredOperationStatus
  created_at: string
  retry_count: number
  last_error?: string
  response?: unknown
}
