/**
 * Charge une donnée du serveur pour un écran : { data, error, loading, reload }.
 * `key` identifie ce qui est chargé (ex. l'id de l'élevage) : quand il change, on recharge.
 * Une réponse arrivée trop tard (l'écran a changé entre-temps) est ignorée.
 *
 * Exemple :
 *   const { data: centres, error, loading } = useResource(identityApi.centers, 'centres')
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '@/lib/api'
import { erreurs } from '@/lib/vocabulaire'

interface State<T> {
  key: string | null
  data?: T
  error?: ApiError
}

export function useResource<T>(load: () => Promise<T>, key: string | null) {
  const loadRef = useRef(load)
  useEffect(() => {
    loadRef.current = load
  })

  const [tick, setTick] = useState(0)
  const [state, setState] = useState<State<T>>({ key: null })
  const fullKey = key === null ? null : `${key}#${tick}`

  useEffect(() => {
    if (fullKey === null) return
    let alive = true
    loadRef.current().then(
      (data) => alive && setState({ key: fullKey, data }),
      (error: unknown) =>
        alive &&
        setState({
          key: fullKey,
          error: error instanceof ApiError ? error : new ApiError('server', erreurs.serveur),
        }),
    )
    return () => {
      alive = false
    }
  }, [fullKey])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  const current = state.key === fullKey
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: fullKey !== null && !current,
    reload,
  }
}
