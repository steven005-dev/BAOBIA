/**
 * Numéros de téléphone ivoiriens : saisie de 10 chiffres, envoi en E.164 (+225...).
 * Le backend normalise aussi : ceci sert à l'affichage et à la saisie.
 *
 * Exemple : formatNationalPhone('0707070707') === '07 07 07 07 07'
 *           toE164('0707070707') === '+2250707070707'
 */

export const COUNTRY_CODE = '225'
export const NATIONAL_LENGTH = 10

export function phoneDigits(text: string): string {
  return text.replace(/\D/g, '').slice(0, NATIONAL_LENGTH)
}

export function formatNationalPhone(digits: string): string {
  return digits.replace(/(\d{2})(?=\d)/g, '$1 ')
}

export function isCompletePhone(digits: string): boolean {
  return digits.length === NATIONAL_LENGTH
}

export function toE164(digits: string): string {
  return `+${COUNTRY_CODE}${digits}`
}
