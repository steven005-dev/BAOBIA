/**
 * Quantité par « − » et « + » (charte : choisir plutôt que taper). Boutons de 60 px,
 * chiffre en grand ; le nombre reste modifiable au clavier numérique.
 *
 * Exemple :
 *   <NumberStepper label={champs.quantite} value={n} onChange={setN} min={1} max={500} />
 */

import { Minus, Plus } from 'lucide-react'
import { useId } from 'react'

import { cn } from '@/lib/utils'
import { mots } from '@/lib/vocabulaire'

export interface NumberStepperProps {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
  className?: string
}

const stepButton =
  'flex size-touch-primary shrink-0 flex-col items-center justify-center rounded-md border-2 border-primary bg-surface text-primary active:bg-accent disabled:border-border disabled:text-muted-foreground'

export function NumberStepper({ label, value, onChange, min = 0, max = 9999, step = 1, className }: NumberStepperProps) {
  const id = useId()
  const clamp = (n: number) => Math.min(max, Math.max(min, n))
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <label htmlFor={id} className="text-body font-bold text-foreground">
        {label}
      </label>
      <div className="flex items-center gap-3">
        <button type="button" className={stepButton} disabled={value <= min} onClick={() => onChange(clamp(value - step))}>
          <Minus aria-hidden className="size-icon" strokeWidth={2.5} />
          <span className="text-caption font-bold">{mots.moins}</span>
        </button>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => {
            const parsed = Number.parseInt(event.target.value, 10)
            onChange(Number.isNaN(parsed) ? min : clamp(parsed))
          }}
          className="h-touch-primary w-full min-w-0 rounded-md border-2 border-input bg-surface text-center text-number font-bold text-foreground focus-visible:border-ring"
        />
        <button type="button" className={stepButton} disabled={value >= max} onClick={() => onChange(clamp(value + step))}>
          <Plus aria-hidden className="size-icon" strokeWidth={2.5} />
          <span className="text-caption font-bold">{mots.plus}</span>
        </button>
      </div>
    </div>
  )
}
