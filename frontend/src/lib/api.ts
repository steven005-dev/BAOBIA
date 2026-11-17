/**
 * Client API BAOBIA. Tous les appels au backend passent par ici.
 *
 * - Base : VITE_API_URL (défaut "/api", relayé vers Django par le proxy Vite).
 * - Ajoute "Authorization: Bearer <access>" et renouvelle le jeton avec le refresh
 *   quand le serveur répond 401 (une seule fois, partagé entre appels simultanés).
 * - Toute erreur devient une ApiError avec un message français simple (`message`).
 *
 * Lecture :   const centres = await api.get<Centre[]>('/centers/')
 * Écriture :  NE PAS appeler api.post directement depuis un écran terrain :
 *             import { submit } from '@/offline' (point d'extension unique de la
 *             future file d'envoi) pour que l'action marche hors ligne.
 */

import { getTokens, setTokens, type Tokens } from './tokens'
import { erreurs } from './vocabulaire'

export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
const TIMEOUT_MS = 15_000

export type ApiErrorKind =
  | 'network'
  | 'timeout'
  | 'session'
  | 'forbidden'
  | 'not_found'
  | 'validation'
  | 'throttled'
  | 'server'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null
  /** Erreurs par champ renvoyées par DRF (ex. { phone: ['Ce champ est obligatoire.'] }). */
  readonly fields: Record<string, string[]>

  constructor(kind: ApiErrorKind, message: string, status: number | null = null,
              fields: Record<string, string[]> = {}) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.fields = fields
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  /** false = pas d'en-tête Authorization ni de renouvellement (connexion). */
  auth?: boolean
  signal?: AbortSignal
}

// ----------------------------------------------------------------- Session expirée

let onSessionExpired: () => void = () => {}

/** Appelé par AuthProvider : que faire quand le refresh ne marche plus. */
export function setSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler
}

// ----------------------------------------------------------------- Requête brute

async function rawFetch(path: string, options: RequestOptions, access: string | null): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort('timeout'), TIMEOUT_MS)
  options.signal?.addEventListener('abort', () => controller.abort(options.signal?.reason))
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (access) headers.Authorization = `Bearer ${access}`
  try {
    return await fetch(`${API_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    })
  } catch {
    if (controller.signal.reason === 'timeout') throw new ApiError('timeout', erreurs.lent)
    if (options.signal?.aborted) throw new DOMException('Annulé', 'AbortError')
    throw new ApiError('network', erreurs.reseau)
  } finally {
    clearTimeout(timer)
  }
}

async function readJson(response: Response): Promise<unknown> {
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function toApiError(status: number, data: unknown): ApiError {
  const body = (data && typeof data === 'object' ? data : {}) as Record<string, unknown>
  const detail = typeof body.detail === 'string' ? body.detail : null
  const fields: Record<string, string[]> = {}
  for (const [key, value] of Object.entries(body)) {
    if (key !== 'detail' && Array.isArray(value)) fields[key] = value.map(String)
  }
  if (status === 401) return new ApiError('session', detail ?? erreurs.sessionExpiree, status)
  if (status === 403) return new ApiError('forbidden', detail ?? erreurs.interdit, status)
  if (status === 404) return new ApiError('not_found', erreurs.introuvable, status)
  if (status === 429) return new ApiError('throttled', detail ?? erreurs.tropDEssais, status)
  if (status >= 500) return new ApiError('server', erreurs.serveur, status)
  return new ApiError('validation', detail ?? erreurs.saisie, status, fields)
}

// ----------------------------------------------------------------- Renouvellement

let refreshing: Promise<Tokens | null> | null = null

/** Un seul renouvellement à la fois, même si dix appels reçoivent 401 ensemble. */
function refreshTokens(): Promise<Tokens | null> {
  const tokens = getTokens()
  if (!tokens) return Promise.resolve(null)
  refreshing ??= (async () => {
    try {
      const response = await rawFetch('/auth/refresh/', { method: 'POST', body: { refresh: tokens.refresh } }, null)
      if (!response.ok) return null
      const data = (await readJson(response)) as { access?: string } | null
      if (!data?.access) return null
      const next = { access: data.access, refresh: tokens.refresh }
      setTokens(next)
      return next
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

// ----------------------------------------------------------------- API publique

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const auth = options.auth ?? true
  let response = await rawFetch(path, options, auth ? getTokens()?.access ?? null : null)

  if (response.status === 401 && auth && getTokens()) {
    let renewed: Tokens | null
    try {
      renewed = await refreshTokens()
    } catch (error) {
      // Réseau coupé pendant le renouvellement : on garde la session (hors ligne).
      if (error instanceof ApiError) throw error
      throw new ApiError('network', erreurs.reseau)
    }
    if (!renewed) {
      setTokens(null)
      onSessionExpired()
      throw new ApiError('session', erreurs.sessionExpiree, 401)
    }
    response = await rawFetch(path, options, renewed.access)
  }

  const data = await readJson(response)
  if (!response.ok) throw toApiError(response.status, data)
  return data as T
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
}
