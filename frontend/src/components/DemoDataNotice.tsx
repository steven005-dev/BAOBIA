/**
 * Mention « données simulées » (charte, section 8). AppLayout l'affiche
 * automatiquement pour un compte de démonstration (user.is_simulated).
 *
 * Exemple : <DemoDataNotice />
 */

import { Info } from 'lucide-react'

import { cn } from '@/lib/utils'
import { messages } from '@/lib/vocabulaire'

export function DemoDataNotice({ className }: { className?: string }) {
  return (
    <p className={cn('flex items-center justify-center gap-2 bg-info-bg px-4 py-2 text-caption font-bold text-info', className)}>
      <Info aria-hidden className="size-icon-small shrink-0" />
      {messages.donneesSimulees}
    </p>
  )
}
