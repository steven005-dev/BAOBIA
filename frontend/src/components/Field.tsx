/**
 * Champ de formulaire : étiquette + aide + erreur, reliés à la saisie pour les
 * lecteurs d'écran (htmlFor, aria-describedby, aria-invalid).
 * L'erreur s'affiche dans un encadré avec icône (charte : jamais une simple couleur).
 *
 * Exemple :
 *   <Field label={champs.telephone} help={champs.telephoneAide} error={erreur}>
 *     <PhoneInput value={tel} onValueChange={setTel} />
 *   </Field>
 */

import { CircleX } from 'lucide-react'
import { useId, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

import { FieldContext } from './fieldContext'

export interface FieldProps {
  label: string
  help?: string
  error?: string | null
  required?: boolean
  className?: string
  children: ReactNode
}

export function Field({ label, help, error, required = false, className, children }: FieldProps) {
  const id = useId()
  const helpId = help ? `${id}-aide` : undefined
  const errorId = error ? `${id}-erreur` : undefined
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined
  return (
    <FieldContext.Provider value={{ id, describedBy, invalid: Boolean(error), required }}>
      <div className={cn('flex flex-col gap-2', className)}>
        <label htmlFor={id} className="text-body font-bold text-foreground">
          {label}
        </label>
        {help && (
          <p id={helpId} className="text-small text-muted-foreground">
            {help}
          </p>
        )}
        {children}
        {error && (
          <p
            id={errorId}
            role="alert"
            className="flex items-start gap-2 rounded-sm border border-error bg-error-bg px-3 py-2 text-small font-bold text-error"
          >
            <CircleX aria-hidden className="mt-0.5 size-icon-badge shrink-0" />
            <span>{error}</span>
          </p>
        )}
      </div>
    </FieldContext.Provider>
  )
}
