/**
 * Icône d'une espèce. Provisoire : les pictogrammes d'espèces (bovin, ovin, caprin, porc,
 * volaille) sont à dessiner (charte, section 5) ; en attendant, Lucide.
 */

import { Bird, PawPrint, type LucideIcon } from 'lucide-react'

export function speciesIcon(code: string): LucideIcon {
  return code === 'poultry' ? Bird : PawPrint
}
