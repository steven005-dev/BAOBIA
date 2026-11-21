/**
 * Outils des écrans santé et alertes (vétérinaire, autorité, éleveur).
 * - useLiveResource : comme useResource, mais recharge tout seul (par défaut toutes les
 *   20 s, seulement quand l'écran est visible) en GARDANT les données affichées : pas de
 *   clignotement. Un signalement envoyé par l'éleveur apparaît chez le vétérinaire sans
 *   recharger la page.
 * - depuis : date relative (« il y a 5 min ») ; la date exacte reste dans le détail.
 * (ListSkeleton.tsx, à côté : place réservée pendant le premier chargement.)
 *
 * Exemple : const alerts = useLiveResource(healthApi.alerts, 'alertes')
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '@/lib/api'
import { erreurs, tempsTextes } from '@/lib/vocabulaire'

export function useLiveResource<T>(load: () => Promise<T>, key: string, intervalMs = 20000) {
  const loadRef = useRef(load)
  useEffect(() => {
    loadRef.current = load
  })
  const [state, setState] = useState<{ key: string; data?: T; error?: ApiError } | null>(null)

  const fetchNow = useCallback(() => {
    let alive = true
    loadRef.current().then(
      (data) => alive && setState({ key, data }),
      (error: unknown) => alive && setState((previous) =>
        // Une erreur pendant un rafraîchissement ne cache pas ce qui est déjà affiché.
        previous?.key === key && previous.data !== undefined
          ? previous
          : { key, error: error instanceof ApiError ? error : new ApiError('server', erreurs.serveur) }),
    )
    return () => {
      alive = false
    }
  }, [key])

  useEffect(() => {
    let cancel = fetchNow()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        cancel()
        cancel = fetchNow()
      }
    }, intervalMs)
    return () => {
      cancel()
      window.clearInterval(timer)
    }
  }, [fetchNow, intervalMs])

  const current = state?.key === key ? state : null
  return {
    data: current?.data,
    error: current?.error,
    loading: current === null,
    reload: fetchNow,
  }
}

/** « à l'instant », « il y a 5 min », « il y a 2 h », « hier », « il y a 3 j », puis la date. */
export function depuis(iso: string, now = Date.now()): string {
  const minutes = Math.round((now - Date.parse(iso)) / 60000)
  if (minutes < 1) return tempsTextes.aLInstant
  if (minutes < 60) return `${tempsTextes.ilYa} ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${tempsTextes.ilYa} ${hours} h`
  const days = Math.floor(hours / 24)
  if (days === 1) return tempsTextes.hier
  if (days < 7) return `${tempsTextes.ilYa} ${days} j`
  return new Date(iso).toLocaleDateString('fr-FR')
}
