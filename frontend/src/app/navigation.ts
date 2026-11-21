/**
 * Entrées de navigation par profil (charte, section 7). 4 entrées métier, puis « Mon compte »
 * en dernier pour tous les profils (À VALIDER : 5 entrées sur téléphone au lieu de 4).
 * Éleveur et agent : Ajouter, Transférer, Recevoir, Signaler sont des tuiles de l'Accueil.
 */

import { Flag, House, Map as MapIcon, PawPrint, ScanQrCode, Siren, UserRound } from 'lucide-react'

import type { RoleCode } from '@/auth/types'
import type { NavItem } from '@/components/BottomNav'
import { mots, profilTextes } from '@/lib/vocabulaire'

const accueil: NavItem = { to: '/', label: mots.accueil, icon: House, end: true }
const animaux: NavItem = { to: '/centres', label: mots.animaux, icon: PawPrint }
const scanner: NavItem = { to: '/scanner', label: mots.scanner, icon: ScanQrCode, emphasis: true }
const alertes: NavItem = { to: '/alertes', label: mots.alertes, icon: Siren }
const signalements: NavItem = { to: '/sante', label: mots.signalements, icon: Flag }
const carte: NavItem = { to: '/carte', label: mots.carte, icon: MapIcon }
const compte: NavItem = {
  to: '/profil', label: profilTextes.titre, shortLabel: profilTextes.ongletCourt, icon: UserRound, bottom: true,
}

/** Éleveur, agent de terrain, commerçant (téléphone). */
export const fieldNavigation: NavItem[] = [accueil, animaux, scanner, alertes, compte]
/** Vétérinaire, autorité (souvent sur ordinateur). */
export const deskNavigation: NavItem[] = [alertes, signalements, carte, animaux, compte]

export function navigationFor(roles: RoleCode[]): NavItem[] {
  return roles.some((role) => role === 'veterinarian' || role === 'authority') ? deskNavigation : fieldNavigation
}
