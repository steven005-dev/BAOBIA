import { ApiError, request } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import {
  setOfflineQueue,
  type OfflineQueue,
  type Operation,
} from '@/offline'

import { db } from './db'
import type { QueuedOperation, StoredOperationStatus } from './types'

const countListeners = new Set<() => void>()
const operationListeners = new Map<
  string,
  Set<(operation: QueuedOperation | undefined) => void>
>()
const sending = new Set<string>()
let currentPendingCount = 0
let installed = false

function notifyOperation(id: string) {
  void db.operations.get(id).then((operation) => {
    operationListeners.get(id)?.forEach((listener) => listener(operation))
  })
}

async function refreshPendingCount() {
  const next = await db.operations.where('status').anyOf('pending', 'sending').count()
  if (next === currentPendingCount) return
  currentPendingCount = next
  countListeners.forEach((listener) => listener())
}

function responseBody(operation: QueuedOperation) {
  if (!operation.body || typeof operation.body !== 'object' || Array.isArray(operation.body)) {
    return operation.body
  }
  return { ...(operation.body as Record<string, unknown>), id: operation.id }
}

async function sendOperation(id: string): Promise<void> {
  if (sending.has(id) || (typeof navigator !== 'undefined' && !navigator.onLine)) return
  const operation = await db.operations.get(id)
  if (!operation || operation.status === 'sent' || operation.status === 'check') return

  sending.add(id)
  await db.operations.update(id, { status: 'sending' })
  notifyOperation(id)
  void refreshPendingCount()

  try {
    const response = await request(operation.path, {
      method: operation.method ?? 'POST',
      body: responseBody(operation),
    })
    await db.operations.update(id, { status: 'sent', response, last_error: undefined })
    notifyOperation(id)
  } catch (error) {
    const isRetryable =
      !(error instanceof ApiError) ||
      ['network', 'timeout', 'session', 'server', 'throttled'].includes(error.kind)
    const status: StoredOperationStatus = isRetryable ? 'pending' : 'check'
    await db.operations.update(id, {
      status,
      retry_count: operation.retry_count + 1,
      last_error: error instanceof Error ? error.message : 'Erreur inconnue',
    })
    notifyOperation(id)
  } finally {
    sending.delete(id)
    void refreshPendingCount()
  }
}

const dexieQueue: OfflineQueue = {
  async submit(operation: Operation) {
    const id = operation.id ?? newUuid()
    const row: QueuedOperation = {
      ...operation,
      id,
      body: responseBody({ ...operation, id, status: 'pending', created_at: '', retry_count: 0 }),
      status: 'pending',
      created_at: new Date().toISOString(),
      retry_count: 0,
    }

    // TR-05 : l'opération est durablement écrite avant toute tentative réseau.
    await db.operations.put(row)
    notifyOperation(id)
    void refreshPendingCount()
    void sendOperation(id)
    return { id, status: 'pending' }
  },
  pendingCount: () => currentPendingCount,
  subscribe(listener) {
    countListeners.add(listener)
    return () => countListeners.delete(listener)
  },
}

export function installMovementQueue(): void {
  setOfflineQueue(dexieQueue)
  if (installed || typeof window === 'undefined') return
  installed = true

  const retryPending = () => {
    void db.operations
      .where('status')
      .anyOf('pending', 'sending')
      .each((operation) => void sendOperation(operation.id))
  }

  window.addEventListener('online', retryPending)
  window.addEventListener('focus', retryPending)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') retryPending()
  })
  void refreshPendingCount()
  retryPending()
}

export function subscribeOperation(
  id: string,
  listener: (operation: QueuedOperation | undefined) => void,
): () => void {
  const listeners = operationListeners.get(id) ?? new Set()
  listeners.add(listener)
  operationListeners.set(id, listeners)
  void db.operations.get(id).then(listener)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) operationListeners.delete(id)
  }
}
