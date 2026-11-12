/** Réponse de GET /api/auth/me/ (backend : accounts/serializers.py, MeSerializer). */

export type RoleCode = 'breeder' | 'field_agent' | 'veterinarian' | 'authority' | 'trader'

export interface MeRole {
  code: RoleCode
  label_fr: string
  organization: { id: string; name: string } | null
  zone: { id: string; code: string; name: string } | null
}

export interface MeCenter {
  id: string
  name: string
  center_type: string
  zone_id: string
  /** Pourquoi l'utilisateur a accès : membre du centre ou mandat. */
  access: 'holder' | 'co_holder' | 'worker' | 'mandate'
  mandate_scope: 'declare' | 'move' | 'all' | null
}

export interface Me {
  id: string
  phone: string
  full_name: string
  language: string
  is_simulated: boolean
  roles: MeRole[]
  has_valid_habilitation: boolean
  accessible_centers: MeCenter[]
}

export interface TokenPair {
  access: string
  refresh: string
}
