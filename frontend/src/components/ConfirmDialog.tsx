/**
 * Fenêtre de confirmation (gabarit « Confirmation » de la charte) : une question, le
 * résumé de l'opération, le bouton Confirmer puis le bouton Retour.
 * Élément natif <dialog> : focus gardé dans la fenêtre, touche Échap = Retour.
 *
 * Exemple :
 *   <ConfirmDialog open={ouvert} title="Confirmer la réception ?"
 *     onConfirm={confirmer} onCancel={() => setOuvert(false)}>
 *     3 animaux venant d'un autre élevage.
 *   </ConfirmDialog>
 *   // Action destructive : variant="danger" confirmLabel={mots.supprimer} confirmIcon={Trash2}
 */

import { ArrowLeft, CircleCheck, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'

import { mots } from '@/lib/vocabulaire'

import { Button } from './Button'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  children?: ReactNode
  confirmLabel?: string
  confirmIcon?: LucideIcon
  cancelLabel?: string
  variant?: 'primary' | 'danger'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = mots.confirmer,
  confirmIcon = CircleCheck,
  cancelLabel = mots.retour,
  variant = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault()
        if (!loading) onCancel()
      }}
      className="m-auto w-[calc(100%-var(--space-8))] max-w-mobile rounded-xl bg-surface p-6 text-foreground shadow-dialog"
    >
      <h2 id={titleId} className="text-subtitle font-bold">
        {title}
      </h2>
      {children && <div className="mt-3 text-body">{children}</div>}
      <div className="mt-6 flex flex-col gap-3">
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          icon={confirmIcon}
          fullWidth
          loading={loading}
          onClick={onConfirm}
          className={variant === 'danger' ? 'h-touch-primary' : undefined}
        >
          {confirmLabel}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} fullWidth disabled={loading} onClick={onCancel}>
          {cancelLabel}
        </Button>
      </div>
    </dialog>
  )
}
