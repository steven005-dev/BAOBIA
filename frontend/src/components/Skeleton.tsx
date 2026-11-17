/**
 * Bloc gris qui réserve la place d'un contenu pendant le chargement (shadcn Skeleton).
 * Invisible pour les lecteurs d'écran : afficher aussi un <Loader /> ou un texte.
 *
 * Exemple : <Skeleton className="h-touch-primary w-full" />
 */

import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-md bg-muted', className)} />
}
