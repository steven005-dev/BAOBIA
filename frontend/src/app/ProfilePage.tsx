/**
 * Mon profil (tous les profils) : qui je suis dans BAOBIA, d'un coup d'œil.
 * Carte d'identité (nom, numéro, rôle en couleur, icône et mot, zone, organisation),
 * habilitation du vétérinaire (seul un vétérinaire habilité valide, RG-08), élevages
 * accessibles, puis « Changer mon mot de passe » et « Déconnexion » (seul endroit pour se
 * déconnecter : l'onglet « Mon compte », pour tous les profils).
 * Données : GET /api/auth/me/ (déjà chargé par AuthProvider), rien de nouveau côté serveur.
 * Accès : la pastille du profil (barre latérale) ou le bandeau sous l'en-tête.
 */

import {
  BadgeCheck, Building2, ChevronRight, KeyRound, LogOut, MapPin, Phone, ShieldAlert, Warehouse,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Card } from '@/components/Card'
import { COUNTRY_CODE, formatNationalPhone } from '@/lib/phone'
import { profileFor, profileStyles } from '@/lib/profiles'
import { cn } from '@/lib/utils'
import { mots, profilTextes, titres } from '@/lib/vocabulaire'

function Row({ icon: Icon, label, children }: { icon: LucideIcon; label: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-primary">
        <Icon aria-hidden className="size-icon" />
      </span>
      <div className="flex min-w-0 flex-col">
        <span className="text-caption font-bold text-muted-foreground">{label}</span>
        <span className="text-body text-foreground">{children}</span>
      </div>
    </div>
  )
}

function displayPhone(phone: string) {
  const national = phone.startsWith(`+${COUNTRY_CODE}`) ? phone.slice(COUNTRY_CODE.length + 1) : phone
  return `+${COUNTRY_CODE} ${formatNationalPhone(national)}`
}

export function ProfilePage() {
  const { user, logout } = useAuth()
  if (!user) return null
  const profile = profileFor(user.roles, user.full_name)
  const style = profile ? profileStyles[profile.role] : null
  const isVet = user.roles.some((r) => r.code === 'veterinarian')
  const organizations = [...new Set(user.roles.map((r) => r.organization?.name).filter(Boolean))]
  const zones = [...new Set(user.roles.map((r) => r.zone?.name).filter(Boolean))]
  const RoleIcon = style?.icon

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{profilTextes.titre}</h1>

      {/* Carte d'identité : couleur, icône et mot du profil (jamais la couleur seule). */}
      <section className="overflow-hidden rounded-xl bg-hero text-primary-foreground shadow-raised">
        <div className="flex items-center gap-4 p-5">
          <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-on-brand-soft font-display text-title font-bold ring-2 ring-on-brand-line">
            {user.full_name.trim().charAt(0).toUpperCase()}
          </span>
          <div className="flex min-w-0 flex-col gap-1.5">
            <span className="truncate font-display text-subtitle font-bold">{user.full_name}</span>
            {style && RoleIcon && (
              <span className={cn('inline-flex items-center gap-1.5 self-start rounded-full border-2 px-3 py-0.5 text-small font-bold', style.soft)}>
                <RoleIcon aria-hidden className="size-icon-small" />
                {[...new Set(user.roles.map((r) => r.label_fr))].join(' · ')}
              </span>
            )}
          </div>
        </div>
      </section>

      <Card>
        <div className="flex flex-col divide-y divide-border/70">
          <Row icon={Phone} label={profilTextes.telephone}>
            <span className="tabular-nums">{displayPhone(user.phone)}</span>
          </Row>
          {zones.length > 0 && <Row icon={MapPin} label={profilTextes.zone}>{zones.join(', ')}</Row>}
          {organizations.length > 0 && (
            <Row icon={Building2} label={profilTextes.organisation}>{organizations.join(', ')}</Row>
          )}
        </div>
      </Card>

      {isVet && (
        <section
          className={cn(
            'flex items-start gap-3 rounded-lg border-2 p-4 shadow-card',
            user.has_valid_habilitation ? 'border-success bg-success-bg text-success' : 'border-warning bg-warning-bg text-warning',
          )}
        >
          {user.has_valid_habilitation
            ? <BadgeCheck aria-hidden className="size-8 shrink-0" />
            : <ShieldAlert aria-hidden className="size-8 shrink-0" />}
          <div className="flex flex-col gap-1">
            <span className="text-card-title font-bold">
              {user.has_valid_habilitation ? profilTextes.habValide : profilTextes.habAbsente}
            </span>
            <span className="text-small">
              {user.has_valid_habilitation ? profilTextes.habValideAide : profilTextes.habAbsenteAide}
            </span>
          </div>
        </section>
      )}

      {user.accessible_centers.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-subtitle font-bold text-foreground">
            {profilTextes.mesElevages} ({user.accessible_centers.length})
          </h2>
          <ul className="flex flex-col gap-2">
            {user.accessible_centers.map((c) => (
              <li key={c.id} className="flex items-center gap-3 rounded-lg border border-border bg-surface p-3 shadow-card">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-primary">
                  <Warehouse aria-hidden className="size-icon" />
                </span>
                <span className="flex-1 font-display text-body font-bold text-foreground">{c.name}</span>
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-caption font-bold text-muted-foreground">
                  {profilTextes.acces[c.access]}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="divide-y divide-border/70 overflow-hidden rounded-xl border border-border/60 bg-surface shadow-card">
        <Link to="/mot-de-passe" className="flex min-h-touch-primary items-center gap-3 px-4 font-display text-body font-bold text-foreground hover:bg-accent">
          <span className="flex size-10 items-center justify-center rounded-md bg-accent text-primary"><KeyRound aria-hidden className="size-icon" /></span>
          <span className="flex-1">{titres.changerMotDePasse}</span>
          <ChevronRight aria-hidden className="size-icon text-muted-foreground" />
        </Link>
        {/* Déconnexion : passe à la couleur « erreur » de la charte au survol et au toucher
            (pas le rouge d'alerte, réservé à une alerte validée). */}
        <button type="button" onClick={() => void logout()} className="group flex min-h-touch-primary w-full items-center gap-3 px-4 text-left font-display text-body font-bold text-foreground transition-colors hover:bg-error-bg hover:text-error focus-visible:bg-error-bg focus-visible:text-error active:bg-error-bg active:text-error">
          <span className="flex size-10 items-center justify-center rounded-md bg-accent text-primary transition-colors group-hover:bg-error group-hover:text-destructive-foreground group-active:bg-error group-active:text-destructive-foreground"><LogOut aria-hidden className="size-icon" /></span>
          <span className="flex-1">{mots.deconnexion}</span>
          <ChevronRight aria-hidden className="size-icon text-muted-foreground group-hover:text-error" />
        </button>
      </div>
    </div>
  )
}
