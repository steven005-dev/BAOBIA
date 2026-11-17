/**
 * Session de l'utilisateur : jetons JWT + profil (GET /api/auth/me/).
 *
 * Hors ligne d'abord : le profil est gardé sur le téléphone, l'application rouvre sans
 * réseau. Le profil est rafraîchi dès que possible. Session expirée (refresh refusé)
 * = retour à l'écran de connexion.
 *
 * Exemple dans un écran :
 *   const { user, hasRole, logout } = useAuth()
 *   if (hasRole('veterinarian') && user?.has_valid_habilitation) { ... }
 * Attention : ces tests servent à l'AFFICHAGE. Les droits sont toujours vérifiés par
 * le serveur.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api, ApiError, setSessionExpiredHandler } from '@/lib/api'
import { toE164 } from '@/lib/phone'
import { getTokens, onTokensChange, setTokens } from '@/lib/tokens'

import type { Me, RoleCode, TokenPair } from './types'

const PROFILE_KEY = 'baobia.me'

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated'

export interface AuthContextValue {
  status: AuthStatus
  /** Null si connecté mais profil pas encore reçu (premier lancement hors ligne). */
  user: Me | null
  /** `phoneDigits` : les 10 chiffres saisis (PhoneInput). Lève une ApiError si refus. */
  login: (phoneDigits: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
  hasRole: (role: RoleCode) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function fetchProfile(): Promise<Me> {
  return api.get<Me>('/auth/me/')
}

function readProfile(): Me | null {
  try {
    const raw = localStorage.getItem(PROFILE_KEY)
    return raw ? (JSON.parse(raw) as Me) : null
  } catch {
    return null
  }
}

function writeProfile(user: Me | null): void {
  try {
    if (user) localStorage.setItem(PROFILE_KEY, JSON.stringify(user))
    else localStorage.removeItem(PROFILE_KEY)
  } catch {
    // Stockage indisponible : le profil reste en mémoire.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(() => (getTokens() ? readProfile() : null))
  const [status, setStatus] = useState<AuthStatus>(() => {
    if (!getTokens()) return 'anonymous'
    return readProfile() ? 'authenticated' : 'loading'
  })

  const clearSession = useCallback(() => {
    writeProfile(null)
    setUser(null)
    setStatus('anonymous')
  }, [])

  const applyProfile = useCallback((me: Me) => {
    writeProfile(me)
    setUser(me)
    setStatus('authenticated')
  }, [])

  const applyProfileError = useCallback((error: unknown) => {
    if (error instanceof ApiError && error.kind === 'session') return // clearSession déjà appelé
    // Réseau absent : on garde la session et le profil connus.
    setStatus((current) => (current === 'loading' ? 'authenticated' : current))
  }, [])

  const refreshProfile = useCallback(
    () => fetchProfile().then(applyProfile, applyProfileError),
    [applyProfile, applyProfileError],
  )

  useEffect(() => {
    setSessionExpiredHandler(clearSession)
    const unsubscribe = onTokensChange((tokens) => {
      if (!tokens) clearSession()
    })
    // Profil rafraîchi au démarrage ; l'état change seulement à la réponse du réseau.
    if (getTokens()) fetchProfile().then(applyProfile, applyProfileError)
    return unsubscribe
  }, [clearSession, applyProfile, applyProfileError])

  const login = useCallback(
    async (phoneDigits: string, password: string) => {
      const tokens = await api.post<TokenPair>(
        '/auth/login/',
        { phone: toE164(phoneDigits), password },
        { auth: false },
      )
      setTokens(tokens)
      setStatus('loading')
      await refreshProfile()
    },
    [refreshProfile],
  )

  const logout = useCallback(async () => {
    const tokens = getTokens()
    if (tokens) {
      try {
        await api.post('/auth/logout/', { refresh: tokens.refresh })
      } catch {
        // Hors ligne : on ferme quand même la session sur le téléphone.
      }
    }
    setTokens(null)
    clearSession()
  }, [clearSession])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login,
      logout,
      refreshProfile,
      hasRole: (role) => Boolean(user?.roles.some((r) => r.code === role)),
    }),
    [status, user, login, logout, refreshProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth doit être utilisé dans <AuthProvider>.')
  return context
}
