import Dexie, { type Table } from 'dexie'
import type { QueuedOperation } from './types'

export class BaobiaDexieDB extends Dexie {
  operations!: Table<QueuedOperation, string>

  constructor() {
    super('baobia_offline_db')
    this.version(1).stores({
      operations: 'id, op_type, status, client_created_at',
    })
  }
}

export const db = new BaobiaDexieDB()
