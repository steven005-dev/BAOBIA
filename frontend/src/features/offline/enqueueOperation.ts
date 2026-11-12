import { db } from './db'
import type { QueuedOperation } from './types'

/**
 * Fonction UNIQUE d'écriture pour tous les formulaires BAOBIA (Règle 8 du projet).
 * Tout formulaire écrit D'ABORD en local dans la base Dexie (IndexedDB),
 * puis déclenche l'envoi en arrière-plan si le réseau est disponible.
 * L'interface utilisateur ne dépend JAMAIS de la réponse immédiate du serveur.
 *
 * @param op_type - Type d'opération (ex: "movement.declare")
 * @param payload - Données du formulaire
 * @param operation_id - UUID optionnel (généré automatiquement si omis)
 * @returns L'identifiant UUID de l'opération
 */
export async function enqueueOperation(
  op_type: string,
  payload: Record<string, any>,
  operation_id?: string
): Promise<string> {
  const id = operation_id || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `op-${Date.now()}-${Math.random()}`)
  const client_created_at = new Date().toISOString()

  const operation: QueuedOperation = {
    id,
    op_type,
    payload,
    client_created_at,
    status: 'pending',
    retry_count: 0,
  }

  // Écriture locale immédiate et inaltérable dans IndexedDB
  await db.operations.put(operation)

  // Déclencher la synchronisation en arrière-plan (sans bloquer le retour utilisateur)
  triggerBackgroundSync(id).catch((err) => {
    console.warn(`[Sync] Envoi en arrière-plan différé pour ${id}:`, err)
  })

  return id
}

/**
 * Tentative d'envoi d'une opération vers l'API.
 * Si le réseau échoue, l'état reste 'pending' pour la prochaine tentative.
 */
async function triggerBackgroundSync(operationId: string): Promise<void> {
  const op = await db.operations.get(operationId)
  if (!op || op.status === 'sent') return

  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    // Hors connexion : reste en attente sans erreur
    return
  }

  try {
    await db.operations.update(operationId, { status: 'sending' })

    const response = await fetch('/api/movements/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...op.payload,
        operation_id: op.id,
      }),
    })

    if (response.ok) {
      const data = await response.json()
      // Ne passe à 'sent' QU'APRÈS confirmation effective du serveur
      await db.operations.update(operationId, {
        status: 'sent',
        server_response: data,
      })
    } else if (response.status >= 400 && response.status < 500) {
      // Erreur de validation ou conflit nécessitant une vérification humaine
      await db.operations.update(operationId, {
        status: 'needs_check',
        last_error: `Erreur serveur (${response.status})`,
      })
    } else {
      // Erreur réseau / serveur 5xx : replacer en 'pending' pour réessai
      await db.operations.update(operationId, {
        status: 'pending',
        retry_count: op.retry_count + 1,
      })
    }
  } catch (err) {
    // Coupure réseau : replacer en 'pending'
    await db.operations.update(operationId, {
      status: 'pending',
      retry_count: op.retry_count + 1,
      last_error: String(err),
    })
  }
}
