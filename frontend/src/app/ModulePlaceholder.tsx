/**
 * Page vide d'un module, en attendant ses écrans. Le responsable du module la
 * remplace dans src/features/<module>/routes.tsx, sans toucher au socle.
 */

import type { LucideIcon } from 'lucide-react'

import { EmptyState } from '@/components/EmptyState'
import { messages } from '@/lib/vocabulaire'

export function ModulePlaceholder({ title, icon }: { title: string; icon: LucideIcon }) {
  return (
    <>
      <h1 className="text-title font-bold text-foreground">{title}</h1>
      <EmptyState icon={icon} title={messages.pageVide} />
    </>
  )
}
