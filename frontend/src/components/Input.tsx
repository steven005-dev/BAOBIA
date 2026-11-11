/**
 * Zone de saisie (charte : TextInput). Texte à 18 px (jamais sous 16 px), 52 px de haut.
 * À placer dans un <Field> pour avoir étiquette, aide et erreur.
 *
 * Exemple :
 *   <Field label={mots.rechercher}><Input type="search" value={q} onChange={...} /></Field>
 *   <Input type="password" end={<Button variant="ghost" icon={Eye}>{mots.afficher}</Button>} />
 */

import type { InputHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/utils'

import { inputClasses, useFieldControl } from './fieldContext'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Élément affiché à droite du champ (ex. bouton Afficher). */
  end?: ReactNode
}

export function Input({ className, end, id, ...props }: InputProps) {
  const field = useFieldControl()
  const input = (
    <input
      id={id ?? field?.id}
      aria-describedby={field?.describedBy}
      aria-invalid={field?.invalid || undefined}
      required={field?.required || undefined}
      className={cn(inputClasses, className)}
      {...props}
    />
  )
  if (!end) return input
  return (
    <div className="flex items-center gap-2">
      {input}
      {end}
    </div>
  )
}
