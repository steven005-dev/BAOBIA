/**
 * Message bref après une action (charte : retour immédiat). Apparaît au-dessus de la
 * navigation basse, se ferme seul (6 s, 10 s pour une erreur) ou avec « Fermer ».
 * Lu par les lecteurs d'écran (aria-live).
 *
 * Exemple :
 *   const toast = useToast()
 *   toast.show(messages.animalAjoute, 'success')
 *   toast.show(erreurs.reseau, 'error')
 * (ToastProvider est déjà posé dans App.tsx.)
 */

import { CircleCheck, CircleX, Info, TriangleAlert, X, type LucideIcon } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'
import { mots } from '@/lib/vocabulaire'

export type ToastVariant = 'success' | 'error' | 'info' | 'warning'

interface ToastItem {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastApi {
  show: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const VARIANTS: Record<ToastVariant, { icon: LucideIcon; classes: string }> = {
  success: { icon: CircleCheck, classes: 'border-success bg-success-bg text-success' },
  error: { icon: CircleX, classes: 'border-error bg-error-bg text-error' },
  info: { icon: Info, classes: 'border-info bg-info-bg text-info' },
  warning: { icon: TriangleAlert, classes: 'border-warning bg-warning-bg text-warning' },
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])

  const show = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = nextId.current++
      setItems((current) => [...current.slice(-2), { id, message, variant }])
      window.setTimeout(() => dismiss(id), variant === 'error' ? 10_000 : 6_000)
    },
    [dismiss],
  )

  const api = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 px-4 pb-[calc(var(--nav-height)+var(--space-4)+env(safe-area-inset-bottom))] lg:pb-6"
      >
        {items.map((item) => (
          <ToastMessage key={item.id} item={item} onClose={() => dismiss(item.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastMessage({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const { icon: Icon, classes } = VARIANTS[item.variant]
  return (
    <div
      role={item.variant === 'error' ? 'alert' : 'status'}
      className={cn(
        'pointer-events-auto flex w-full max-w-mobile items-center gap-3 rounded-md border-2 py-2 pr-2 pl-4 shadow-dialog',
        classes,
      )}
    >
      <Icon aria-hidden className="size-icon shrink-0" />
      <p className="flex-1 text-body font-bold">{item.message}</p>
      <button
        type="button"
        onClick={onClose}
        className="flex h-touch shrink-0 items-center gap-1 rounded-sm px-2 text-caption font-bold"
      >
        <X aria-hidden className="size-icon-badge" />
        {mots.fermer}
      </button>
    </div>
  )
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast doit être utilisé dans <ToastProvider>.')
  return context
}
