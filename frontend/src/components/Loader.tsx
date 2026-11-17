/**
 * Chargement en cours (charte : LoadingState) : icône qui tourne + texte.
 * Pour réserver la place d'un contenu, voir Skeleton.
 *
 * Exemple :
 *   <Loader />                         // « Chargement… »
 *   <Loader label="Envoi…" fullPage />
 */

import { LoaderCircle } from 'lucide-react'

import { cn } from '@/lib/utils'
import { messages } from '@/lib/vocabulaire'

export interface LoaderProps {
  label?: string
  /** Centre le chargement sur toute la hauteur de l'écran. */
  fullPage?: boolean
  className?: string
}

export function Loader({ label = messages.chargement, fullPage = false, className }: LoaderProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex items-center justify-center gap-3 py-6 text-body font-bold text-muted-foreground',
        fullPage && 'min-h-dvh',
        className,
      )}
    >
      <LoaderCircle aria-hidden className="size-icon animate-spin text-primary" />
      <span>{label}</span>
    </div>
  )
}
