import { api } from '@/lib/api'

export interface DestinationShareCode {
  code: string
  expires_in_days: number
}

export interface ResolvedDestination {
  center_id: string
  center_name: string
}

export type MovementStatus = 'declared' | 'confirmed' | 'partial' | 'disputed' | 'cancelled' | 'expired'

export interface MovementItem {
  unit: string
  unit_kind: 'animal' | 'lot'
  unit_local_name: string | null
  quantity_sent: number
  quantity_received: number | null
}

export interface MovementConfirmation {
  id: string
  side: 'sender' | 'receiver'
  decision: 'confirm' | 'refuse' | 'confirm_with_discrepancy'
  /** MV-04 : « assisted » = saisi par un agent mandaté, jamais présenté comme direct. */
  mode: 'direct' | 'assisted'
  entered_by_name: string
  occurred_at: string
  clock_suspect: boolean
}

export interface MovementDiscrepancy {
  id: string
  unit: string | null
  unit_local_name: string | null
  kind: 'missing' | 'extra' | 'count_mismatch' | 'identity_mismatch'
  quantity_expected: number | null
  quantity_found: number | null
}

export interface Movement {
  id: string
  movement_type: 'transfer' | 'sale' | 'slaughter' | 'temporary' | 'return'
  from_center: string
  from_center_name: string
  to_center: string | null
  to_center_name: string | null
  to_party_note: string | null
  status: MovementStatus
  occurred_at: string
  received_at: string | null
  is_simulated: boolean
  items: MovementItem[]
  status_events: { id: string; status: MovementStatus; reason: string | null; occurred_at: string }[]
  confirmations: MovementConfirmation[]
  discrepancies: MovementDiscrepancy[]
  clock_suspect: boolean
}

export const MOVEMENT_STATUS_LABELS: Record<MovementStatus, string> = {
  declared: 'En attente de confirmation',
  confirmed: 'Confirmé',
  partial: 'Reçu avec écart',
  disputed: 'Contesté',
  cancelled: 'Annulé',
  expired: 'Expiré',
}

/** Motifs proposés (choisir plutôt qu'écrire, UX-04). */
export const REASONS = {
  refuse: ['Animaux non conformes', 'Pas d’accord sur la vente', 'Animaux non arrivés'],
  cancel: ['Erreur de saisie', 'Vente annulée', 'Animaux restés à l’élevage'],
  contest: ['Animaux non conformes', 'Paiement non reçu', 'Pas d’accord sur le nombre'],
} as const

export const movementApi = {
  shareDestinationCode: (centerId: string) =>
    api.post<DestinationShareCode>('/movements/destination-code/', { center_id: centerId }),
  resolveDestinationCode: (code: string) =>
    api.get<ResolvedDestination>(`/movements/destination-code/?code=${encodeURIComponent(code)}`),
  /** Mouvements d'un élevage (en ligne). */
  list: (centerId: string) =>
    api.get<Movement[]>(`/movements/?center_id=${encodeURIComponent(centerId)}`),
  /** Détail vu depuis un des deux élevages (en ligne), ex. pour compter à la réception. */
  detail: (movementId: string, centerId: string) =>
    api.get<Movement>(`/movements/${movementId}/?center_id=${encodeURIComponent(centerId)}`),
}
