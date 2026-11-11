/**
 * Jetons JWT gardés sur le téléphone (localStorage) : l'application doit rouvrir
 * hors ligne sans redemander la connexion. Seuls api.ts et AuthProvider y touchent.
 */

export interface Tokens {
  access: string
  refresh: string
}

const KEY = 'baobia.tokens'
type Listener = (tokens: Tokens | null) => void
const listeners = new Set<Listener>()

function read(): Tokens | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Tokens>
    return parsed.access && parsed.refresh ? { access: parsed.access, refresh: parsed.refresh } : null
  } catch {
    return null
  }
}

let current: Tokens | null = read()

export function getTokens(): Tokens | null {
  return current
}

export function setTokens(tokens: Tokens | null): void {
  current = tokens
  try {
    if (tokens) localStorage.setItem(KEY, JSON.stringify(tokens))
    else localStorage.removeItem(KEY)
  } catch {
    // Stockage indisponible (navigation privée) : on garde en mémoire seulement.
  }
  listeners.forEach((listener) => listener(tokens))
}

export function onTokensChange(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
