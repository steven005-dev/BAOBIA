/**
 * Position du téléphone À L'INSTANT d'un scan (règle absolue 8 : jamais de suivi continu).
 * Renvoie null si refusée, indisponible ou trop lente : le scan ne dépend jamais d'elle.
 */

import type { Position } from './api'

export function currentPosition(timeoutMs = 4000): Promise<Position | null> {
  if (!('geolocation' in navigator)) return Promise.resolve(null)
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({
          latitude: Number(p.coords.latitude.toFixed(6)),
          longitude: Number(p.coords.longitude.toFixed(6)),
          accuracy_m: Number(Math.min(p.coords.accuracy, 999999).toFixed(1)),
        }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: 60_000 },
    )
  })
}
