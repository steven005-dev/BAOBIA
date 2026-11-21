/**
 * Accueil (charte v2, section 7) : un bandeau d'accueil, puis les grandes actions du terrain
 * en tuiles, une couleur par action (jamais une couleur d'état sanitaire). Chaque tuile
 * mène à l'écran du module concerné. Pas de logique métier ici.
 */

import { ArrowLeftRight, ChevronRight, CirclePlus, Flag, KeyRound, LogOut, PackageCheck, QrCode, UserPlus } from 'lucide-react'
import { Link, Navigate } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { BigChoiceTile } from '@/components/BigChoiceTile'
import { UnreadMessages } from '@/features/notifications/UnreadMessages'
import { profileFor, profileStyles } from '@/lib/profiles'
import { accueilTextes, mots, titres } from '@/lib/vocabulaire'

function firstName(fullName?: string) {
  return fullName?.split(' ')[0] ?? ''
}

export function HomePage() {
  const { user, logout, hasRole } = useAuth()
  // Vétérinaire et autorité : pas d'Accueil terrain, on ouvre les alertes (charte, section 7).
  if (hasRole('veterinarian') || hasRole('authority')) return <Navigate to="/alertes" replace />
  const profile = user ? profileFor(user.roles, user.full_name) : null
  const style = profile ? profileStyles[profile.role] : null
  const today = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="flex flex-col gap-6">
      <section className="relative overflow-hidden rounded-xl bg-hero p-5 text-primary-foreground shadow-raised">
        <p className="text-small text-on-brand-muted first-letter:uppercase">{today}</p>
        <h1 className="mt-1 text-title font-bold">
          {accueilTextes.bonjour} {firstName(user?.full_name)}
        </h1>
        {style && (
          <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-on-brand-soft px-3 py-1 text-small font-bold">
            <style.icon aria-hidden className="size-icon-small" />
            {style.label}
            {profile?.zone && <span className="font-normal text-on-brand-muted">· {profile.zone}</span>}
          </p>
        )}
        <img src="/baobia-icon.svg" alt="" aria-hidden
             className="pointer-events-none absolute -right-6 -bottom-8 size-36 rotate-6 opacity-20" />
      </section>

      <UnreadMessages />

      <section className="flex flex-col gap-3">
        <h2 className="text-subtitle font-bold text-foreground">{accueilTextes.queVoulezVousFaire}</h2>
        <div className="grid grid-cols-2 gap-3">
          <BigChoiceTile to="/centres" icon={CirclePlus} label={mots.ajouter} tone="brand" />
          <BigChoiceTile to="/mouvements" icon={ArrowLeftRight} label={mots.transferer} tone="teal" />
          <BigChoiceTile to="/mouvements/recevoir" icon={PackageCheck} label={mots.recevoir} tone="indigo" />
          <BigChoiceTile to="/sante" icon={Flag} label={mots.signaler} tone="violet" />
          {hasRole('field_agent') && <BigChoiceTile to="/eleveurs/nouveau" icon={UserPlus} label={mots.inscrire} tone="earth" />}
          {hasRole('field_agent') && <BigChoiceTile to="/etiquettes" icon={QrCode} label={mots.etiquettes} tone="slate" />}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-subtitle font-bold text-foreground">{accueilTextes.monCompte}</h2>
        <div className="divide-y divide-border/70 overflow-hidden rounded-xl border border-border/60 bg-surface shadow-card">
          <Link to="/mot-de-passe" className="flex min-h-touch-primary items-center gap-3 px-4 font-display text-body font-bold text-foreground hover:bg-accent">
            <span className="flex size-10 items-center justify-center rounded-md bg-accent text-primary"><KeyRound aria-hidden className="size-icon" /></span>
            <span className="flex-1">{titres.changerMotDePasse}</span>
            <ChevronRight aria-hidden className="size-icon text-muted-foreground" />
          </Link>
          <button type="button" onClick={() => void logout()} className="flex min-h-touch-primary w-full items-center gap-3 px-4 text-left font-display text-body font-bold text-foreground hover:bg-accent">
            <span className="flex size-10 items-center justify-center rounded-md bg-accent text-primary"><LogOut aria-hidden className="size-icon" /></span>
            <span className="flex-1">{mots.quitter}</span>
            <ChevronRight aria-hidden className="size-icon text-muted-foreground" />
          </button>
        </div>
      </section>
    </div>
  )
}
