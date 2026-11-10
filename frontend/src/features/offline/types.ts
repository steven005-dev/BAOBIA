export type OperationStatus = 'pending' | 'sending' | 'sent' | 'needs_check' | 'failed'

export interface QueuedOperation {
  id: string // UUID v4/v7 généré sur l'appareil
  op_type: string // ex: "movement.declare", "movement.confirm"
  payload: Record<string, any>
  client_created_at: string // ISO 8601
  status: OperationStatus
  retry_count: number
  last_error?: string
  server_response?: Record<string, any>
}
