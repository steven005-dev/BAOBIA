/**
 * Écran de connexion : numéro de téléphone + mot de passe, une seule action.
 * Message d'erreur neutre (le serveur ne dit pas si c'est le numéro ou le mot de passe).
 */

import { Eye, EyeOff, LogIn } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { PhoneInput } from '@/components/PhoneInput'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import { ApiError } from '@/lib/api'
import { isCompletePhone } from '@/lib/phone'
import { APP_NAME, champs, erreurs, mots, titres } from '@/lib/vocabulaire'

import { useAuth } from './AuthProvider'

export function LoginPage() {
  const { status, login } = useAuth()
  const online = useOnlineStatus()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (status === 'authenticated') return <Navigate to={from} replace />

  const phoneError = submitted && !isCompletePhone(phone) ? erreurs.telephoneIncomplet : null
  const passwordError = submitted && !password ? erreurs.motDePasseVide : null

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitted(true)
    setError(null)
    if (!isCompletePhone(phone) || !password) return
    if (!online) {
      setError(erreurs.reseau)
      return
    }
    setLoading(true)
    try {
      await login(phone, password)
      navigate(from, { replace: true })
    } catch (caught) {
      // 401 : « Numéro ou mot de passe incorrect. » ; 429 : « Trop d'essais... » (texte du serveur).
      setError(caught instanceof ApiError ? caught.message : erreurs.serveur)
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="bg-primary px-4 pt-[env(safe-area-inset-top)] text-primary-foreground">
        <p className="mx-auto max-w-mobile py-6 text-display font-bold">{APP_NAME}</p>
      </header>
      <OfflineIndicator variant="banner" />
      <main className="mx-auto flex w-full max-w-mobile flex-1 flex-col px-4 py-6">
        <h1 className="mb-6 text-title font-bold text-foreground">{titres.connexion}</h1>
        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
          <Field label={champs.telephone} help={champs.telephoneAide} error={phoneError} required>
            <PhoneInput value={phone} onValueChange={setPhone} autoFocus disabled={loading} />
          </Field>
          <Field label={champs.motDePasse} error={passwordError} required>
            <Input
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={loading}
              end={
                <Button
                  variant="ghost"
                  icon={showPassword ? EyeOff : Eye}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((shown) => !shown)}
                  className="h-touch-secondary"
                >
                  {showPassword ? mots.cacher : mots.afficher}
                </Button>
              }
            />
          </Field>
          {error && <Banner variant="error">{error}</Banner>}
          <Button type="submit" icon={LogIn} fullWidth loading={loading}>
            {mots.seConnecter}
          </Button>
        </form>
      </main>
    </div>
  )
}
