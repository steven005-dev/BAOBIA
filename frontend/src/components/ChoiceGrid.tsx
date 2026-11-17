/**
 * Choix visuel par grandes icônes (espèce, symptômes), 2 colonnes sur téléphone.
 * Un seul choix (single) ou plusieurs (multiple). Charte : choisir plutôt que taper.
 *
 * Exemple :
 *   <ChoiceGrid label={champs.espece} value={espece} onChange={setEspece}
 *     options={[{ value: 'cattle', label: 'Bovin', icon: PawPrint }, ...]} />
 *   <ChoiceGrid multiple label={mots.symptomes} value={coches} onChange={setCoches} options={...} />
 */

import type { LucideIcon } from 'lucide-react'
import { useId } from 'react'

import { cn } from '@/lib/utils'

import { BigChoiceTile } from './BigChoiceTile'

export interface ChoiceOption {
  value: string
  label: string
  icon: LucideIcon
}

interface CommonProps {
  label: string
  options: ChoiceOption[]
  className?: string
}

type SingleProps = CommonProps & { multiple?: false; value: string | null; onChange: (value: string) => void }
type MultipleProps = CommonProps & { multiple: true; value: string[]; onChange: (value: string[]) => void }

export function ChoiceGrid(props: SingleProps | MultipleProps) {
  const labelId = useId()
  const isSelected = (value: string) =>
    props.multiple ? props.value.includes(value) : props.value === value

  const toggle = (value: string) => {
    if (props.multiple) {
      props.onChange(isSelected(value) ? props.value.filter((v) => v !== value) : [...props.value, value])
    } else {
      props.onChange(value)
    }
  }

  return (
    <div className={cn('flex flex-col gap-3', props.className)}>
      <p id={labelId} className="text-body font-bold text-foreground">
        {props.label}
      </p>
      <div
        role={props.multiple ? 'group' : 'radiogroup'}
        aria-labelledby={labelId}
        className="grid grid-cols-2 gap-3 sm:grid-cols-3"
      >
        {props.options.map((option) => (
          <BigChoiceTile
            key={option.value}
            icon={option.icon}
            label={option.label}
            role={props.multiple ? 'checkbox' : 'radio'}
            selected={isSelected(option.value)}
            onClick={() => toggle(option.value)}
          />
        ))}
      </div>
    </div>
  )
}
