/**
 * Appels API du module identity (backend : apps/identity/views.py, apps/core/views.py).
 * Lectures par api.get ; écritures par submit() (file hors ligne, voir src/offline).
 */

import { api } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { submit } from '@/offline'

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
  animal: { sex: string; birth_date: string | null; breed: string | null; marks: string | null } | null
  lot: { current_size: number; description: string | null } | null
  created_at: string
  is_simulated: boolean
}

export interface ScanResult {
  result: 'found' | 'replaced' | 'lost'
  message: string
  label_code: string
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

export const identityApi = {
  species: () => api.get<Species[]>('/species/'),
  centers: () => api.get<CenterItem[]>('/centers/'),
  centerUnits: (centerId: string) => api.get<UnitItem[]>(`/centers/${centerId}/units/`),
  unit: (unitId: string) => api.get<Unit>(`/units/${unitId}/`),
  scan: (code: string) => api.get<ScanResult>(`/scan/${encodeURIComponent(code)}/`),

  /**
   * Ajoute un animal ou un lot. `id` est créé une fois par formulaire : renvoyer le même
   * (double appui, réseau qui coupe) est sans effet côté serveur.
   */
  addUnit: (id: string, unit: NewUnit) =>
    submit({ type: 'unit.register', path: '/units/', id, body: { id, ...unit } }),

  /** Change l'étiquette. Rejouer le même changement est sans effet côté serveur. */
  replaceLabel: (unitId: string, labelCode: string, reason: ReplaceReason) =>
    submit({
      type: 'unit.replace_label',
      path: `/units/${unitId}/label/`,
      body: { label_code: labelCode, reason },
    }),
}

export { newUuid }
