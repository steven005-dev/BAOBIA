/**
 * Résumé d'un animal ou d'un lot dans une liste (charte, section 8) : code court très
 * visible, nom local, espèce, état sanitaire. Toute la carte est cliquable si `to`.
 *
 * Exemple :
 *   <AnimalCard shortCode="23456789N" name="Animal 1" species="Bovin" state="normal"
 *               to={`/centres/animaux/${id}`} />
 */

import { ChevronRight, PawPrint, Users } from 'lucide-react'
import { Link } from 'react-router'

import type { HealthState } from '@/lib/healthStates'
import { formatShortCode } from '@/lib/shortCode'
import { cn } from '@/lib/utils'

import { StatusBadge } from './StatusBadge'

export interface AnimalCardProps {
  shortCode?: string | null
  name?: string | null
  species: string
  kind?: 'animal' | 'lot'
  /** Effectif d'un lot. */
  size?: number
  state?: HealthState
  to?: string
  className?: string
}

export function AnimalCard({ shortCode, name, species, kind = 'animal', size, state, to, className }: AnimalCardProps) {
  const Icon = kind === 'lot' ? Users : PawPrint
  const body = (
    <>
      <span className="flex size-touch shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <Icon aria-hidden className="size-icon" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-card-title font-bold tracking-wider">{shortCode ? formatShortCode(shortCode) : '—'}</span>
        <span className="truncate text-small text-muted-foreground">
          {[name, species, kind === 'lot' && size ? `${size}` : null].filter(Boolean).join(' · ')}
        </span>
        {state && <StatusBadge state={state} className="self-start" />}
      </span>
      {to && <ChevronRight aria-hidden className="size-icon shrink-0 text-muted-foreground" />}
    </>
  )
  const classes = cn('flex items-center gap-3 rounded-lg border border-border bg-card p-4 shadow-card', className)
  return to ? (
    <Link to={to} className={cn(classes, 'active:bg-accent')}>
      {body}
    </Link>
  ) : (
    <div className={classes}>{body}</div>
  )
}
