/**
 * Appels API du module identity (backend : apps/identity/views.py, apps/core/views.py).
 * Lectures par api.get ; écritures par submit() (file hors ligne, voir src/offline).
 */

import { api } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { ApiError } from '@/lib/api'
import { submit, submitAndWait, type Operation, type WaitResult } from '@/offline'

export type TrackingMode = 'animal' | 'lot' | 'both'
export type UnitKind = 'animal' | 'lot'

export interface Species {
  id: string
  code: string
  label_fr: string
  tracking_mode: TrackingMode
}

export interface CenterItem {
  id: string
  name: string
  center_type: string
  zone_id: string
  access: 'holder' | 'co_holder' | 'worker' | 'mandate'
}

export interface UnitItem {
  id: string
  kind: UnitKind
  species: Species
  local_name: string | null
  life_status: string
  label_code: string | null
  /** Numéro officiel de la boucle (15 chiffres, groupés par 3) ; null si l'animal n'en a pas. */
  official_number: string | null
  size: number
}

export interface Unit {
  id: string
  kind: UnitKind
  species: Species
  local_name: string | null
  life_status: string
  current_center: { id: string; name: string } | null
  label_code: string | null
  official_number: string | null
  animal: { sex: string; birth_date: string | null; breed: string | null; marks: string | null } | null
  lot: { current_size: number; description: string | null } | null
  created_at: string
  is_simulated: boolean
}

export interface ScanResult {
  result: 'found' | 'replaced' | 'lost'
  message: string
  label_code: string | null
  /** false : vue réduite, l'animal n'est pas dans les élevages de l'utilisateur. */
  full_access: boolean
  unit: Unit | null
  species: Species
}

export interface NewUnit {
  kind: UnitKind
  center_id: string
  species_id: string
  label_code: string
  size?: number
}

export type ReplaceReason = 'lost' | 'damaged' | 'error'

export interface Zone {
  id: string
  name: string
  level: number
  parent_id: string | null
}

export interface NewCenter {
  name: string
  zone_id: string
  species_ids: string[]
}

/** Agent de terrain : un éleveur et son premier élevage (ids créés sur le téléphone). */
export interface NewBreeder {
  id: string
  full_name: string
  phone: string
  password: string
  center_id: string
  center_name: string
  zone_id: string
  species_ids: string[]
  /** L'agent a lu la notice à l'éleveur, qui accepte. */
  consent: true
}

export interface Position {
  latitude: number
  longitude: number
  accuracy_m: number
}

/**
 * Envoie et attend la réponse (voir submitAndWait). Une erreur de saisie levée par la file
 * directe devient un résultat « check » : les écrans n'ont qu'un seul cas à traiter.
 */
async function send(operation: Operation): Promise<WaitResult> {
  try {
    return await submitAndWait(operation)
  } catch (err) {
    if (err instanceof ApiError && (err.kind === 'validation' || err.kind === 'forbidden' || err.kind === 'not_found')) {
      return { id: operation.id ?? '', status: 'check', error: err.message }
    }
    throw err
  }
}

export const identityApi = {
  species: () => api.get<Species[]>('/species/'),
  centers: () => api.get<CenterItem[]>('/centers/'),
  centerUnits: (centerId: string) => api.get<UnitItem[]>(`/centers/${centerId}/units/`),
  unit: (unitId: string) => api.get<Unit>(`/units/${unitId}/`),
  scan: (code: string) => api.get<ScanResult>(`/scan/${encodeURIComponent(code)}/`),
  zones: () => api.get<Zone[]>('/centers/zones/'),

  /** Ajoute un élevage ; l'utilisateur en devient le détenteur. Rejouable (même id). */
  addCenter: (id: string, center: NewCenter) =>
    send({ type: 'center.create', path: '/centers/', id, body: { id, center_type: 'farm', ...center } }),

  /**
   * Agent de terrain : inscrit un éleveur (compte, élevage, mandat pour ajouter ses animaux).
   * Rejouable : même `id` et `center_id` = sans effet côté serveur.
   */
  registerBreeder: (breeder: NewBreeder) =>
    send({ type: 'breeder.register', path: '/breeders/', id: breeder.id, body: breeder }),

  /** Garde la trace d'un scan réussi (le résultat est calculé par le serveur). */
  recordVerification: (unitId: string, labelCode: string, method: 'scan' | 'manual_code',
                       position: Position | null) => {
    const id = newUuid()
    return submit({
      type: 'unit.verify',
      path: `/units/${unitId}/verifications/`,
      id,
      body: {
        id, label_code: labelCode, method, occurred_at: new Date().toISOString(),
        ...(position ?? {}),
      },
    })
  },

  /** Agent de terrain : remet des étiquettes vierges à un élevage (tout ou rien). */
  issueLabels: (centerId: string, codes: string[]) =>
    send({ type: 'label.issue', path: `/centers/${centerId}/labels/`, body: { codes } }),

  /**
   * Ajoute un animal ou un lot. `id` est créé une fois par formulaire : renvoyer le même
   * (double appui, réseau qui coupe) est sans effet côté serveur.
   */
  addUnit: (id: string, unit: NewUnit) =>
    send({ type: 'unit.register', path: '/units/', id, body: { id, ...unit } }),

  /** Change l'étiquette. Rejouer le même changement est sans effet côté serveur. */
  replaceLabel: (unitId: string, labelCode: string, reason: ReplaceReason) =>
    send({
      type: 'unit.replace_label',
      path: `/units/${unitId}/label/`,
      body: { label_code: labelCode, reason },
    }),
}

export { newUuid }
