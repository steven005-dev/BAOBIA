/**
 * Marque de profil : chaque espace (éleveur, vétérinaire, autorité...) a sa couleur,
 * son icône et son mot, visibles sur tous les écrans (en-tête et barre latérale).
 * Couleurs : variables --role-* de globals.css (À VALIDER par le chef).
 *
 * Exemple : const profile = profileFor(user.roles)
 *           <ProfileBar profile={profile} />
 */

import { ClipboardCheck, Fence, Landmark, type LucideIcon, Stethoscope, Store } from 'lucide-react'

import type { MeRole, RoleCode } from '@/auth/types'

import { profils } from './vocabulaire'

export interface ProfileStyle {
  label: string
  icon: LucideIcon
  /** Fond plein et texte blanc (bandeau). */
  solid: string
  /** Fond clair, texte et contour de la couleur du profil (pastille). */
  soft: string
}

// Classes écrites en entier pour que Tailwind les génère.
export const profileStyles: Record<RoleCode, ProfileStyle> = {
  breeder: {
    label: profils.breeder, icon: Fence,
    solid: 'bg-role-breeder text-primary-foreground',
    soft: 'bg-role-breeder-bg text-role-breeder border-role-breeder',
  },
  field_agent: {
    label: profils.field_agent, icon: ClipboardCheck,
    solid: 'bg-role-field-agent text-primary-foreground',
    soft: 'bg-role-field-agent-bg text-role-field-agent border-role-field-agent',
  },
  trader: {
    label: profils.trader, icon: Store,
    solid: 'bg-role-trader text-primary-foreground',
    soft: 'bg-role-trader-bg text-role-trader border-role-trader',
  },
  veterinarian: {
    label: profils.veterinarian, icon: Stethoscope,
    solid: 'bg-role-veterinarian text-primary-foreground',
    soft: 'bg-role-veterinarian-bg text-role-veterinarian border-role-veterinarian',
  },
  authority: {
    label: profils.authority, icon: Landmark,
    solid: 'bg-role-authority text-primary-foreground',
    soft: 'bg-role-authority-bg text-role-authority border-role-authority',
  },
}

/** Ordre de priorité quand un compte a plusieurs rôles : celui qui décide le plus. */
const PRIORITY: RoleCode[] = ['veterinarian', 'authority', 'field_agent', 'trader', 'breeder']

export interface Profile {
  role: RoleCode
  /** Nom de la personne connectée. */
  name?: string
  /** Zone couverte (vétérinaire, autorité, agent). */
  zone?: string
}

export function profileFor(roles: MeRole[], name?: string): Profile | null {
  const role = PRIORITY.map((code) => roles.find((r) => r.code === code)).find(Boolean)
  if (!role) return null
  return { role: role.code, name, zone: role.zone?.name }
}
