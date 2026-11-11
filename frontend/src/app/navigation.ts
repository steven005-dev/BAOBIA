/**
 * Entrées de navigation par profil (charte, section 7). 4 entrées au plus.
 * Éleveur et agent : Ajouter, Transférer, Recevoir, Signaler sont des tuiles de l'Accueil.
 */

import { Flag, House, Map as MapIcon, PawPrint, ScanQrCode, Siren } from 'lucide-react'

import type { RoleCode } from '@/auth/types'
import type { NavItem } from '@/components/BottomNav'
import { mots } from '@/lib/vocabulaire'

const accueil: NavItem = { to: '/', label: mots.accueil, icon: House, end: true }
const animaux: NavItem = { to: '/centres', label: mots.animaux, icon: PawPrint }
const scanner: NavItem = { to: '/scanner', label: mots.scanner, icon: ScanQrCode, emphasis: true }
const alertes: NavItem = { to: '/alertes', label: mots.alertes, icon: Siren }
const signalements: NavItem = { to: '/sante', label: mots.signalements, icon: Flag }
const carte: NavItem = { to: '/carte', label: mots.carte, icon: MapIcon }

/** Éleveur, agent de terrain, commerçant (téléphone). */
export const fieldNavigation: NavItem[] = [accueil, animaux, scanner, alertes]
/** Vétérinaire, autorité (souvent sur ordinateur). */
export const deskNavigation: NavItem[] = [alertes, signalements, carte, animaux]

export function navigationFor(roles: RoleCode[]): NavItem[] {
  return roles.some((role) => role === 'veterinarian' || role === 'authority') ? deskNavigation : fieldNavigation
}
