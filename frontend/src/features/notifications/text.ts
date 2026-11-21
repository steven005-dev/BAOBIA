/**
 * Texte, icône et lien d'un message (tous les profils). Le serveur n'envoie qu'un code et
 * des valeurs simples ; le texte vient du vocabulaire. Jamais le nom d'un élevage.
 */

import { ArrowLeftRight, CircleCheck, Clock, Flag, Siren, Stethoscope, TriangleAlert, type LucideIcon } from 'lucide-react'

import { textesDecisionSignalement, textesNotifications } from '@/lib/vocabulaire'

import type { AppNotification, NotificationKind } from './api'

const KIND_ICONS: Record<NotificationKind, LucideIcon> = {
  exposure: TriangleAlert,
  alert: Siren,
  zone_cluster_review: Stethoscope,
  escalation: Clock,
  review: Stethoscope,
  report: Flag,
  movement: ArrowLeftRight,
}
const MESSAGE_ICONS: Record<string, LucideIcon> = { 'exposure.ended': CircleCheck, 'movement.confirmed': CircleCheck }

export function messageIcon(n: AppNotification): LucideIcon {
  return MESSAGE_ICONS[n.message_code] ?? KIND_ICONS[n.kind] ?? TriangleAlert
}

/** Texte affiché ; null si le code est inconnu de cette version de l'application. */
export function messageText(n: AppNotification): string | null {
  if (n.message_code === 'report.reviewed') {
    return textesDecisionSignalement[String(n.params.decision)] ?? textesDecisionSignalement.close ?? null
  }
  const template = textesNotifications[n.message_code]
  if (!template) return null
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = n.params[key]
    if (key === 'species') return value ? ` (${String(value).toLowerCase()})` : ''
    return value === undefined || value === '' ? '—' : String(value)
  })
}

/** Où mène le message quand on le touche (null : nulle part). */
export function messageLink(n: AppNotification, professional: boolean): string | null {
  const code = n.message_code
  if (code.startsWith('report.') && n.params.report_id) return `/sante/${String(n.params.report_id)}`
  if (code === 'movement.to_confirm') return '/mouvements/recevoir'
  if (code.startsWith('movement.')) return '/mouvements/historique'
  if (professional && n.alert_id) return `/alertes/${n.alert_id}`
  if (code.startsWith('exposure.')) return '/alertes'
  return null
}
