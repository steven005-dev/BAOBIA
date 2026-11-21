/** Place réservée pendant le premier chargement d'une liste (squelette, pas de rond qui tourne). */

import { Skeleton } from '@/components/Skeleton'
import { messages } from '@/lib/vocabulaire'

/** Trois lignes grises à la place d'une liste qui se charge. */
export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4 shadow-card">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ))}
      <span className="sr-only">{messages.chargement}</span>
    </div>
  )
}
