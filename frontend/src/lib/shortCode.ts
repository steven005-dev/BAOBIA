/**
 * Code court des étiquettes (9 caractères : 8 + 1 caractère de contrôle).
 * MÊME algorithme que le backend (identity/services.py : Luhn mod 32).
 * Alphabet sans 0, O, 1, I pour éviter les confusions à la lecture et à la dictée.
 *
 * Exemple : normalizeShortCode(' abcd-efgh j ') === 'ABCDEFGHJ'
 *           isValidShortCode('23456789N') === true
 */

export const SHORT_CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
export const SHORT_CODE_LENGTH = 9

/** Majuscules, garde seulement les caractères autorisés, coupe à 9. */
export function normalizeShortCode(text: string): string {
  return [...text.toUpperCase()]
    .filter((char) => SHORT_CODE_ALPHABET.includes(char))
    .join('')
    .slice(0, SHORT_CODE_LENGTH)
}

/** Affichage pour la lecture et la dictée : « ABCD EFGH J ». */
export function formatShortCode(code: string): string {
  return [code.slice(0, 4), code.slice(4, 8), code.slice(8)].filter(Boolean).join(' ')
}

export function isValidShortCode(code: string): boolean {
  if (code.length !== SHORT_CODE_LENGTH) return false
  const n = SHORT_CODE_ALPHABET.length
  let factor = 1
  let sum = 0
  for (const char of [...code].reverse()) {
    const index = SHORT_CODE_ALPHABET.indexOf(char)
    if (index < 0) return false
    const addend = factor * index
    sum += Math.floor(addend / n) + (addend % n)
    factor = factor === 2 ? 1 : 2
  }
  return sum % n === 0
}
