/**
 * Saisie du code court d'une étiquette (9 caractères). Met en majuscules, refuse
 * 0, O, 1, I et tout autre caractère, affiche le code en groupes « ABCD EFGH J ».
 * `value` = le code sans espace. Vérifier avec isValidShortCode(value) avant l'envoi.
 *
 * Exemple :
 *   const [code, setCode] = useState('')
 *   const erreur = code.length === 9 && !isValidShortCode(code) ? erreurs.codeIncorrect : null
 *   <Field label={champs.codeEtiquette} help={champs.codeEtiquetteAide} error={erreur}>
 *     <CodeInput value={code} onValueChange={setCode} />
 *   </Field>
 */

import type { InputHTMLAttributes } from 'react'

import { formatShortCode, normalizeShortCode } from '@/lib/shortCode'
import { cn } from '@/lib/utils'

import { inputClasses, useFieldControl } from './fieldContext'

export interface CodeInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type'> {
  value: string
  onValueChange: (code: string) => void
}

export function CodeInput({ value, onValueChange, className, id, ...props }: CodeInputProps) {
  const field = useFieldControl()
  return (
    <input
      id={id ?? field?.id}
      type="text"
      autoCapitalize="characters"
      autoComplete="off"
      autoCorrect="off"
      spellCheck={false}
      aria-describedby={field?.describedBy}
      aria-invalid={field?.invalid || undefined}
      required={field?.required || undefined}
      value={formatShortCode(value)}
      onChange={(event) => onValueChange(normalizeShortCode(event.target.value))}
      className={cn(inputClasses, 'text-center text-subtitle font-bold tracking-widest uppercase', className)}
      {...props}
    />
  )
}
