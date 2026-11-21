/**
 * Appels API santé, alertes et carte (backend : apps/health, apps/alerts).
 * Contrat avec la file hors ligne : docs/CONTRAT_SANTE_MOUVEMENTS.md.
 * - Signaler (terrain) : opération `health_report.submit` par la file (submitAndWait).
 * - Décision du vétérinaire (bureau) : en ligne seulement, appel direct.
 */

import { ApiError, api } from '@/lib/api'
import { newUuid } from '@/lib/uuid'
import { submitAndWait, type WaitResult } from '@/offline'

import type { AlertLevel } from '@/components/AlertLevelBadge'
import type { HealthState } from '@/lib/healthStates'

export type ReportKind = 'suspicion' | 'death' | 'abnormal_mortality'
export type ReportStatus = 'submitted' | 'under_review' | 'validated' | 'rejected' | 'closed'
export type Decision =
  | 'request_info' | 'retain_suspicion' | 'raise_level2' | 'validate_level3' | 'dismiss' | 'close'

export interface CatalogItem {
  code: string
  label_fr: string
  icon: string | null
}

/** Piste de maladie (apps/health/leads.py) : aide au vétérinaire, jamais un diagnostic. */
export interface DiseaseLead {
  disease: { code: string; label_fr: string; is_notifiable: boolean }
  strength: 'strong' | 'medium' | 'weak'
  strength_label: string
  major_found: number
  major_total: number
  explanation: string[]
  spread: string
  incubation_days: [number, number]
  zoonosis: boolean
  samples: { nature: string; conditioning: string }[]
}

export interface Leads {
  items: DiseaseLead[]
  profiles_version: number
  validated: boolean
  lab_note: string
  warning: string
}

export interface Report {
  id: string
  /** zone_name : vétérinaire et autorité seulement. */
  center: { id: string; name: string; zone_id: string; zone_name?: string }
  report_kind: ReportKind
  affected_count: number
  /** Dont morts (v1.4) ; malades = affected_count - dead_count. */
  dead_count: number
  self_severity: 'low' | 'medium' | 'high'
  note: string | null
  status: ReportStatus
  occurred_at: string
  created_at: string
  is_simulated: boolean
  symptoms: CatalogItem[]
  /** code (étiquette) : vétérinaire et autorité seulement. */
  subjects: { unit_id: string; condition: string; species_code: string; local_name: string | null; code?: string | null }[]
  /** Pistes de maladie : vétérinaire et autorité seulement. */
  leads?: Leads
  /** Seulement pour un vétérinaire ou une autorité de la zone. */
  reviews?: { id: string; decision: Decision; disease: CatalogItem | null; note: string | null;
              vet_name: string; occurred_at: string }[]
}

export interface NewReport {
  center_id: string
  report_kind: ReportKind
  affected_count: number
  dead_count: number
  self_severity: 'low' | 'medium' | 'high'
  occurred_at: string
  symptom_codes: string[]
  subjects: { unit_id: string; condition: 'sick' | 'dead' }[]
  latitude?: number
  longitude?: number
  position_accuracy_m?: number
  position_source?: 'gps' | 'none'
}

export interface AlertSummary {
  id: string
  level: AlertLevel
  status: 'open' | 'monitoring' | 'closed' | 'cancelled'
  trigger_kind: 'single_report' | 'zone_cluster'
  confidence: 'normal' | 'reduced'
  disease: { code: string; label_fr: string } | null
  species: { code: string; label_fr: string } | null
  zone: { id: string; name: string }
  focus_center: { id: string; name: string } | null
  opened_at: string
  validated_at: string | null
  validated_by: string | null
  exposed_count: number
  excluded_count: number
  is_simulated: boolean
}

export interface AlertDetail extends AlertSummary {
  rule: { version: number; lookback_days: number; lookforward_days: number; max_depth: number;
          include_unconfirmed: boolean; experimental: boolean }
  reports: { id: string; occurred_at: string; affected_count: number; status: ReportStatus }[]
  exposures: {
    center: { id: string; name: string }
    status: 'exposed' | 'excluded_negative' | 'monitoring' | 'cleared'
    depth: number
    last_contact_at: string | null
    path: { step: number; from: string; to: string; occurred_at: string; reason: string
            /** declared = déclaré d'un seul côté ; disputed = contesté (spec v1.4, 9.6). */
            movement_status?: string }[]
  }[]
}

export interface ZoneState {
  zone: { id: string; code: string; name: string; level: number; parent_id: string | null }
  state: HealthState
  is_masked: boolean
  centers_count: number | null
  animals_count: number | null
  computed_at: string
}

export interface MapPoint {
  latitude: string
  longitude: string
  zone_id: string
  type: string
}

export interface MapData {
  zones: ZoneState[]
  my_centers: { id: string; name: string; zone_id: string; latitude: string | null; longitude: string | null }[]
  /** Points des élevages de ses zones : vétérinaire et autorité seulement (sinon vide). */
  points?: MapPoint[]
}

/** Une erreur de saisie de la file directe devient un résultat « check » (un seul cas). */
async function send(operation: Parameters<typeof submitAndWait>[0]): Promise<WaitResult> {
  try {
    return await submitAndWait(operation)
  } catch (err) {
    if (err instanceof ApiError && ['validation', 'forbidden', 'not_found'].includes(err.kind)) {
      return { id: operation.id ?? '', status: 'check', error: err.message }
    }
    throw err
  }
}

export const healthApi = {
  symptoms: (species?: string) =>
    api.get<CatalogItem[]>(`/symptoms/${species ? `?species=${encodeURIComponent(species)}` : ''}`),
  diseases: (species?: string) =>
    api.get<CatalogItem[]>(`/diseases/${species ? `?species=${encodeURIComponent(species)}` : ''}`),
  reports: () => api.get<Report[]>('/health-reports/'),
  report: (id: string) => api.get<Report>(`/health-reports/${id}/`),

  /** Signaler. `id` est créé une fois par formulaire : renvoyer le même est sans effet. */
  submitReport: (id: string, report: NewReport) =>
    send({ type: 'health_report.submit', path: '/health-reports/', id, body: { id, ...report } }),

  /** Décision du vétérinaire (en ligne). */
  review: (reportId: string, decision: Decision, diseaseCode?: string, note?: string) =>
    api.post<{ report_status: ReportStatus }>(`/health-reports/${reportId}/review/`, {
      id: newUuid(), decision, disease_code: diseaseCode ?? '', note: note ?? '',
    }),

  alerts: () => api.get<AlertSummary[]>('/alerts/'),
  alert: (id: string) => api.get<AlertDetail>(`/alerts/${id}/`),
  map: (species?: string) =>
    api.get<MapData>(`/map/zones/${species ? `?species=${encodeURIComponent(species)}` : ''}`),
}

export { newUuid }
