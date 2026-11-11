import { createContext, useContext } from 'react'

/** Identifiants partagés entre <Field> et la saisie qu'il contient (accessibilité). */
export interface FieldControl {
  id: string
  describedBy: string | undefined
  invalid: boolean
  required: boolean
}

export const FieldContext = createContext<FieldControl | null>(null)

/** Utilisé par Input, PhoneInput, CodeInput, Select pour se relier à leur <Field>. */
export function useFieldControl(): FieldControl | null {
  return useContext(FieldContext)
}

/** Classes communes des zones de saisie : 52 px de haut, texte à 18 px (jamais sous 16 px). */
export const inputClasses = [
  'h-touch-secondary w-full min-w-0 rounded-md border-2 border-input bg-surface px-4',
  'text-body text-foreground placeholder:text-muted-foreground',
  'focus-visible:border-ring',
  'aria-invalid:border-error',
  'disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground',
].join(' ')
