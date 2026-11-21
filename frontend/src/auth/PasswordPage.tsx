/**
 * Changer mon mot de passe (ex. l'éleveur remplace celui que l'agent lui a remis).
 * En ligne seulement : un mot de passe ne passe jamais par la file hors ligne.
 */

import { ArrowLeft, Eye, EyeOff, KeyRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { useToast } from '@/components/Toast'
import { api, ApiError } from '@/lib/api'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

const MIN_LENGTH = 8

export function PasswordPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [shown, setShown] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const nextError = submitted && next.length < MIN_LENGTH ? erreurs.motDePasseCourt : null

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitted(true)
    if (!current || next.length < MIN_LENGTH) return
    setSending(true)
    setError(null)
    try {
      await api.post('/auth/password/', { current_password: current, new_password: next })
      toast.show(messages.motDePasseChange, 'success')
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  const type = shown ? 'text' : 'password'
  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{titres.changerMotDePasse}</h1>
      <Field label={champs.motDePasseActuel} error={submitted && !current ? erreurs.motDePasseVide : null} required>
        <Input type={type} autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </Field>
      <Field label={champs.nouveauMotDePasse} help={champs.nouveauMotDePasseAide} error={nextError} required>
        <Input type={type} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
      </Field>
      <Button variant="ghost" icon={shown ? EyeOff : Eye} aria-pressed={shown} onClick={() => setShown((s) => !s)} className="self-start">
        {shown ? mots.cacher : mots.afficher}
      </Button>
      {error && <Banner variant="error">{error}</Banner>}
      <div className="flex flex-col gap-3">
        <Button type="submit" icon={KeyRound} loading={sending}>
          {mots.modifier}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)} disabled={sending}>
          {mots.retour}
        </Button>
      </div>
    </form>
  )
}
