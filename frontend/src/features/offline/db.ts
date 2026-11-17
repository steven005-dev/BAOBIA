import Dexie, { type Table } from 'dexie'
import type { QueuedOperation } from './types'

export class BaobiaDexieDB extends Dexie {
  operations!: Table<QueuedOperation, string>

  constructor() {
    super('baobia_offline_db')
    this.version(1).stores({
      operations: 'id, op_type, status, client_created_at',
    })
    this.version(2)
      .stores({ operations: 'id, type, status, created_at, path' })
      .upgrade(async (transaction) => {
        await transaction.table('operations').toCollection().modify((row) => {
          const operation = row as Record<string, unknown>
          operation.type = operation.op_type ?? 'movement.declare'
          operation.path = '/movements/'
          operation.method = 'POST'
          operation.body = {
            ...((operation.payload as Record<string, unknown> | undefined) ?? {}),
            id: operation.id,
          }
          operation.created_at = operation.client_created_at ?? new Date().toISOString()
          operation.retry_count = operation.retry_count ?? 0
          if (operation.status === 'needs_check' || operation.status === 'failed') {
            operation.status = 'check'
          } else if (operation.status === 'sending') {
            operation.status = 'pending'
          }
          delete operation.op_type
          delete operation.payload
          delete operation.client_created_at
          delete operation.server_response
        })
      })
  }
}

export const db = new BaobiaDexieDB()
