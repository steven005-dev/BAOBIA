/**
 * POINT D'EXTENSION de la file d'envoi hors ligne (responsable : Konan Romuald).
 *
 * Aujourd'hui : pas de file. submit() envoie directement au serveur et pendingCount
 * reste à 0. Les écrans terrain appellent DÉJÀ submit() : quand la vraie file
 * existera, il suffira de remplacer `directQueue` par elle, sans toucher aux écrans.
 *
 * Contrat attendu de la future file (charte, section 10) :
 * - écrire d'abord en local, puis envoyer ; l'écran ne dépend jamais de la réponse ;
 * - chaque opération a un UUID créé sur l'appareil (rejouer = sans effet côté serveur) ;
 * - états : "pending" (En attente), "sent" (Envoyé, seulement après réponse du serveur),
 *   "check" (À vérifier : conflit, vérification humaine).
 *
 * Exemple :
 *   import { submit } from '@/offline'
 *   await submit({ type: 'movement.declare', path: '/movements/', body: { ... } })
 */

import { request } from '@/lib/api'
import { newUuid } from '@/lib/uuid'

export type OperationStatus = 'pending' | 'sent' | 'check'

export interface Operation {
  /** Type métier, ex. "movement.declare", "health_report.submit". */
  type: string
  /** Route API, ex. "/movements/". */
  path: string
  method?: 'POST' | 'PUT' | 'PATCH'
  body: unknown
  /** UUID de l'opération (créé ici si absent) : clé d'idempotence. */
  id?: string
}

export interface SubmitResult {
  id: string
  status: OperationStatus
  /** Réponse du serveur quand l'envoi a déjà eu lieu. */
  response?: unknown
}

export interface OfflineQueue {
  submit(operation: Operation): Promise<SubmitResult>
  /** Nombre d'opérations pas encore confirmées par le serveur. */
  pendingCount(): number
  /** Prévient quand le nombre change ; retourne la fonction de désabonnement. */
  subscribe(listener: () => void): () => void
}

/** Implémentation provisoire : envoi direct, aucune mise en file. */
const directQueue: OfflineQueue = {
  async submit(operation) {
    const id = operation.id ?? newUuid()
    const response = await request(operation.path, {
      method: operation.method ?? 'POST',
      body: operation.body,
    })
    return { id, status: 'sent', response }
  },
  pendingCount: () => 0,
  subscribe: () => () => {},
}

let queue: OfflineQueue = directQueue

/** Pour Romuald : brancher la vraie file ici (une seule ligne à changer à l'usage). */
export function setOfflineQueue(next: OfflineQueue): void {
  queue = next
}

export function submit(operation: Operation): Promise<SubmitResult> {
  return queue.submit(operation)
}

export function getPendingCount(): number {
  return queue.pendingCount()
}

export function subscribePending(listener: () => void): () => void {
  return queue.subscribe(listener)
}
