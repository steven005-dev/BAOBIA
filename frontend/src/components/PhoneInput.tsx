/**
 * Numéro de téléphone ivoirien : l'indicatif +225 est affiché, l'utilisateur tape ses
 * 10 chiffres (clavier numérique), groupés par deux pour la lecture : 07 07 07 07 07.
 * `value` = les chiffres seuls ; toE164(value) donne +2250707070707.
 *
 * Exemple :
 *   const [tel, setTel] = useState('')
 *   <Field label={champs.telephone}><PhoneInput value={tel} onValueChange={setTel} /></Field>
 */

import { Phone } from 'lucide-react'
import type { InputHTMLAttributes } from 'react'

import { COUNTRY_CODE, formatNationalPhone, phoneDigits } from '@/lib/phone'
import { cn } from '@/lib/utils'

import { inputClasses, useFieldControl } from './fieldContext'

export interface PhoneInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type'> {
  value: string
  onValueChange: (digits: string) => void
}

export function PhoneInput({ value, onValueChange, className, id, ...props }: PhoneInputProps) {
  const field = useFieldControl()
  return (
    <div className="flex items-stretch gap-2">
      <span
        aria-hidden
        className="flex h-touch-secondary shrink-0 items-center gap-1 rounded-md border-2 border-input bg-muted px-3 text-body font-bold text-foreground"
      >
        <Phone className="size-icon-small" />+{COUNTRY_CODE}
      </span>
      <input
        id={id ?? field?.id}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        aria-describedby={field?.describedBy}
        aria-invalid={field?.invalid || undefined}
        required={field?.required || undefined}
        value={formatNationalPhone(value)}
        onChange={(event) => onValueChange(phoneDigits(event.target.value))}
        className={cn(inputClasses, 'tracking-wide', className)}
        {...props}
      />
    </div>
  )
}
