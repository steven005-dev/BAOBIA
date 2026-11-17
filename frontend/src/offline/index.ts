/**
 * Point d'entrée partagé par les écrans terrain pour la file d'envoi hors ligne.
 * Le module movements installe l'implémentation Dexie au chargement de ses routes.
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

/** État d'une opération suivie (`watch`). `error` : message du serveur si refusée. */
export interface OperationState {
  status: OperationStatus
  response?: unknown
  error?: string
}

export interface OfflineQueue {
  submit(operation: Operation): Promise<SubmitResult>
  /** Suit une opération jusqu'à son envoi ou son refus ; retourne la fonction d'arrêt. */
  watch?(id: string, listener: (state: OperationState) => void): () => void
  /** Nombre d'opérations pas encore confirmées par le serveur. */
  pendingCount(): number
  /** Prévient quand le nombre change ; retourne la fonction de désabonnement. */
  subscribe(listener: () => void): () => void
}

/** File directe de secours tant qu'aucune file persistante n'est installée. */
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

/** Permet aux modules terrain d'installer leur file persistante. */
export function setOfflineQueue(next: OfflineQueue): void {
  queue = next
}

export function submit(operation: Operation): Promise<SubmitResult> {
  return queue.submit(operation)
}

/** Résultat de submitAndWait : envoyé, refusé (« check », avec `error`) ou encore en attente. */
export interface WaitResult {
  id: string
  status: OperationStatus
  response?: unknown
  error?: string
}

/**
 * Pour un écran qui a besoin de la réponse (afficher la fiche créée, une erreur de saisie) :
 * écrit dans la file comme submit(), puis attend jusqu'à `timeoutMs` la réponse du serveur.
 * - "sent"    : le serveur a accepté (`response`) ;
 * - "check"   : le serveur a refusé (`error`, message lisible) ;
 * - "pending" : pas de réponse à temps (hors ligne, réseau lent) : l'opération reste
 *               gardée sur le téléphone et partira toute seule ; l'écran l'annonce.
 * Avec la file directe (sans file persistante), une erreur du serveur est levée (ApiError).
 */
export async function submitAndWait(operation: Operation, timeoutMs = 8000): Promise<WaitResult> {
  const result = await queue.submit(operation)
  const watch = queue.watch?.bind(queue)
  if (result.status !== 'pending' || !watch) return result
  return new Promise<WaitResult>((resolve) => {
    // `stopper.fn` est posé après watch() ; le listener peut répondre avant (déjà envoyé).
    const stopper: { fn?: () => void } = {}
    let done = false
    const finish = (state: WaitResult) => {
      if (done) return
      done = true
      clearTimeout(timer)
      stopper.fn?.()
      resolve(state)
    }
    const timer = setTimeout(() => finish({ id: result.id, status: 'pending' }), timeoutMs)
    stopper.fn = watch(result.id, (state) => {
      if (state.status !== 'pending') finish({ id: result.id, ...state })
    })
    if (done) stopper.fn()
  })
}

export function getPendingCount(): number {
  return queue.pendingCount()
}

export function subscribePending(listener: () => void): () => void {
  return queue.subscribe(listener)
}
