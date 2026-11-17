/**
 * Les 5 états sanitaires (charte, section 2) : UNE seule définition pour toute
 * l'application (badges, légende et zones de la carte, listes).
 * Chaque état = couleur + contour sombre + icône + mot : jamais la couleur seule.
 * Le rouge (alert) est réservé à une alerte VALIDÉE par un vétérinaire.
 */

import { CircleHelp, Eye, ShieldCheck, Siren, TriangleAlert, type LucideIcon } from 'lucide-react'

import { etatsSanitaires } from './vocabulaire'

export type HealthState = 'normal' | 'watch' | 'exposure' | 'alert' | 'unknown'

export interface HealthStateStyle {
  label: string
  icon: LucideIcon
  /** Classes Tailwind : fond, texte, contour (variables du thème). */
  classes: string
}

export const HEALTH_STATES: Record<HealthState, HealthStateStyle> = {
  normal: {
    label: etatsSanitaires.normal,
    icon: ShieldCheck,
    classes: 'bg-health-normal text-health-normal-fg border-health-normal-line',
  },
  watch: {
    label: etatsSanitaires.watch,
    icon: Eye,
    classes: 'bg-health-watch text-health-watch-fg border-health-watch-line',
  },
  exposure: {
    label: etatsSanitaires.exposure,
    icon: TriangleAlert,
    classes: 'bg-health-exposure text-health-exposure-fg border-health-exposure-line',
  },
  alert: {
    label: etatsSanitaires.alert,
    icon: Siren,
    classes: 'bg-health-alert text-health-alert-fg border-health-alert-line',
  },
  unknown: {
    label: etatsSanitaires.unknown,
    icon: CircleHelp,
    classes: 'bg-health-unknown text-health-unknown-fg border-health-unknown-line',
  },
}

/** Ordre d'affichage (légende). */
export const HEALTH_STATE_ORDER: HealthState[] = ['normal', 'watch', 'exposure', 'alert', 'unknown']
