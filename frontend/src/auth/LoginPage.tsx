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
import { accueilTextes, APP_NAME, champs, erreurs, mots, titres } from '@/lib/vocabulaire'

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
    <div className="flex min-h-dvh flex-col bg-background lg:flex-row">
      {/* Bandeau de la marque : en haut sur téléphone, moitié gauche sur ordinateur. */}
      <header className="relative overflow-hidden bg-hero px-6 pt-[env(safe-area-inset-top)] pb-14 text-primary-foreground lg:flex lg:w-1/2 lg:flex-col lg:justify-center lg:px-16 lg:pb-0">
        <div className="mx-auto w-full max-w-mobile pt-8 lg:max-w-md lg:pt-0">
          <p className="flex items-center gap-3 font-display text-display font-bold tracking-wide">
            <img src="/baobia-icon.svg" alt="" className="size-14 rounded-lg ring-2 ring-on-brand-line" />
            {APP_NAME}
          </p>
          <p className="mt-4 text-body text-on-brand-muted lg:text-subtitle">{accueilTextes.slogan}</p>
          <ul className="mt-5 flex flex-wrap gap-2">
            {accueilTextes.piliers.map((pilier) => (
              <li key={pilier} className="rounded-full bg-on-brand-soft px-3 py-1 font-display text-small font-bold">
                {pilier}
              </li>
            ))}
          </ul>
        </div>
        <img src="/baobia-icon.svg" alt="" aria-hidden
             className="pointer-events-none absolute -right-10 -bottom-12 size-48 rotate-6 opacity-15 lg:size-96" />
      </header>
      <main className="mx-auto -mt-8 flex w-full max-w-mobile flex-1 flex-col px-4 pb-8 lg:mt-0 lg:max-w-none lg:items-center lg:justify-center lg:px-16">
        <div className="w-full rounded-xl bg-surface p-6 shadow-raised lg:max-w-md lg:p-8">
        <OfflineIndicator variant="banner" />
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
        </div>
      </main>
    </div>
  )
}
