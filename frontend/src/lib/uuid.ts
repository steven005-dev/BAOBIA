/**
 * UUID v4 créé sur l'appareil (le hors ligne crée ses identifiants sans le serveur).
 * crypto.randomUUID n'existe pas sur une page servie en http (test sur téléphone via
 * l'adresse du PC) : on retombe alors sur crypto.getRandomValues, disponible partout.
 */
export function newUuid(): string {
  if (typeof crypto.randomUUID === 'function' && window.isSecureContext) {
    return crypto.randomUUID()
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = ((bytes[6] ?? 0) & 0x0f) | 0x40
  bytes[8] = ((bytes[8] ?? 0) & 0x3f) | 0x80
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
