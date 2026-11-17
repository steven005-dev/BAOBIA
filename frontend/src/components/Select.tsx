/**
 * Liste de choix (menu natif du téléphone : grand, connu, accessible).
 * Pour 2 à 6 choix visuels, préférer ChoiceGrid (charte : choisir plutôt que taper).
 *
 * Exemple :
 *   <Field label={champs.espece}>
 *     <Select value={espece} onChange={(e) => setEspece(e.target.value)}
 *             placeholder={champs.choisir}
 *             options={[{ value: 'cattle', label: 'Bovin' }, { value: 'goat', label: 'Chèvre' }]} />
 *   </Field>
 */

import { ChevronDown } from 'lucide-react'
import type { SelectHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

import { inputClasses, useFieldControl } from './fieldContext'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  options: SelectOption[]
  placeholder?: string
}

export function Select({ options, placeholder, className, id, ...props }: SelectProps) {
  const field = useFieldControl()
  return (
    <div className="relative">
      <select
        id={id ?? field?.id}
        aria-describedby={field?.describedBy}
        aria-invalid={field?.invalid || undefined}
        required={field?.required || undefined}
        className={cn(inputClasses, 'appearance-none pr-12', className)}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-4 size-icon -translate-y-1/2 text-foreground"
      />
    </div>
  )
}
