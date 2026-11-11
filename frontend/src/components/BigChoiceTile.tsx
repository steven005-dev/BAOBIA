/**
 * Grosse tuile à icône (charte : IconTextButton, grandes actions de l'Accueil, et
 * élément de ChoiceGrid). Icône 48 px + mot. Trois usages :
 * - lien :   <BigChoiceTile to="/mouvements" icon={ArrowLeftRight} label={mots.transferer} />
 * - action : <BigChoiceTile onClick={...} icon={Flag} label={mots.signaler} />
 * - choix :  <BigChoiceTile role="radio" selected={choisi} onClick={...} ... />
 *   (sélection signalée par contour épais + coche + mot, pas seulement la couleur)
 */

import { CircleCheck, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'

import { cn } from '@/lib/utils'

export interface BigChoiceTileProps {
  icon: LucideIcon
  label: string
  description?: string
  /** Lien interne (react-router). */
  to?: string
  onClick?: () => void
  /** Pour un choix : "radio" (un seul) ou "checkbox" (plusieurs). */
  role?: 'radio' | 'checkbox'
  selected?: boolean
  disabled?: boolean
  className?: string
}

const base = [
  'relative flex min-h-28 w-full flex-col items-center justify-center gap-2 rounded-lg border-2 p-4 text-center',
  'bg-surface text-foreground shadow-card transition-colors',
  'active:bg-accent disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground',
].join(' ')

export function BigChoiceTile({
  icon: Icon,
  label,
  description,
  to,
  onClick,
  role,
  selected = false,
  disabled = false,
  className,
}: BigChoiceTileProps) {
  const classes = cn(base, selected ? 'border-primary border-[length:var(--border-focus)] bg-accent' : 'border-border', className)
  const content = (
    <>
      {selected && (
        <CircleCheck aria-hidden className="absolute top-2 right-2 size-icon text-primary" strokeWidth={2.5} />
      )}
      <Icon aria-hidden className="size-icon-empty text-primary" strokeWidth={1.75} />
      <span className="text-body font-bold">{label}</span>
      {description && <span className="text-small text-muted-foreground">{description}</span>}
    </>
  )
  if (to && !disabled) {
    return (
      <Link to={to} className={classes}>
        {content}
      </Link>
    )
  }
  return (
    <button
      type="button"
      role={role}
      aria-checked={role ? selected : undefined}
      disabled={disabled}
      onClick={onClick}
      className={classes}
    >
      {content}
    </button>
  )
}

/** Nom de la charte (section 8). */
export const IconTextButton = BigChoiceTile
