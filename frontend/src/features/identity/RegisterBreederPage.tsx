/**
 * Inscrire un éleveur (agent de terrain, en face de l'éleveur) : son nom, son numéro, son
 * premier élevage. Pas d'inscription libre dans BAOBIA : c'est l'agent qui crée le compte.
 * Le mot de passe est CRÉÉ PAR LE TÉLÉPHONE (8 chiffres, faciles à dicter) et affiché à la
 * fin pour être remis à l'éleveur. L'agent reçoit un mandat « declare » sur l'élevage : il
 * peut ajouter les animaux tout de suite. Identifiants créés ici : envoi rejouable.
 */

import { ArrowLeft, House, PawPrint, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { PhoneInput } from '@/components/PhoneInput'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { formatNationalPhone, isCompletePhone, toE164 } from '@/lib/phone'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, newUuid } from './api'
import { speciesIcon } from './speciesIcon'
import { useResource } from './useResource'
import { zoneOptions, zonesWithin } from './zones'

const PASSWORD_LENGTH = 8

/** 8 chiffres au hasard (crypto) : se dicte et se tape sur un clavier de téléphone. */
function generatePassword(): string {
  const random = new Uint32Array(PASSWORD_LENGTH)
  crypto.getRandomValues(random)
  return [...random].map((n) => String(n % 10)).join('')
}

/** « 4827 1930 » : lecture et dictée. */
function formatPassword(password: string): string {
  return password.replace(/(\d{4})(?=\d)/, '$1 ')
}

export function RegisterBreederPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const zones = useResource(identityApi.zones, 'zones')
  const species = useResource(identityApi.species, 'especes')

  const [breederId] = useState(newUuid)
  const [centerId] = useState(newUuid)
  const [password, setPassword] = useState(generatePassword)
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [centerName, setCenterName] = useState('')
  const [zoneId, setZoneId] = useState('')
  const [speciesIds, setSpeciesIds] = useState<string[]>([])
  const [submitted, setSubmitted] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<'sent' | 'pending' | null>(null)

  if (zones.loading || species.loading) return <Loader />
  const loadError = zones.error ?? species.error
  if (loadError) return <Banner variant="error">{loadError.message}</Banner>

  // Secteur de l'agent : ses zones et leurs zones filles (le serveur vérifie aussi).
  const sector = (user?.roles ?? []).filter((r) => r.code === 'field_agent' && r.zone).map((r) => r.zone!.id)
  const choices = zoneOptions(zonesWithin(zones.data ?? [], sector))
  const phoneError = submitted && !isCompletePhone(phone) ? erreurs.telephoneIncomplet : null

  const send = async () => {
    setSubmitted(true)
    if (!fullName.trim() || !isCompletePhone(phone) || !centerName.trim() || !zoneId || speciesIds.length === 0) {
      setError(messages.champManquant)
      return
    }
    setSending(true)
    setError(null)
    const breeder = (pwd: string) => ({
      id: breederId,
      full_name: fullName.trim(),
      phone: toE164(phone),
      password: pwd,
      center_id: centerId,
      center_name: centerName.trim(),
      zone_id: zoneId,
      species_ids: speciesIds,
    })
    try {
      let result = await identityApi.registerBreeder(breeder(password))
      if (result.status === 'check' && result.error?.toLowerCase().includes('mot de passe')) {
        // Mot de passe refusé (trop courant, rare) : on en crée un autre et on réessaie une fois.
        const fresh = generatePassword()
        setPassword(fresh)
        result = await identityApi.registerBreeder(breeder(fresh))
      }
      if (result.status === 'check') setError(result.error ?? erreurs.saisie)
      else setDone(result.status === 'sent' ? 'sent' : 'pending')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  if (done) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-title font-bold text-foreground">{titres.inscrireEleveur}</h1>
        {done === 'sent' ? (
          <Banner variant="success" title={messages.eleveurInscrit}>{messages.remettreIdentifiants}</Banner>
        ) : (
          <Banner variant="info" title={messages.enAttente}>{messages.inscriptionEnAttente}</Banner>
        )}
        <Card title={fullName.trim()} icon={UserPlus}>
          <dl className="flex flex-col gap-3">
            <div>
              <dt className="text-caption text-muted-foreground">{champs.telephone}</dt>
              <dd className="text-subtitle font-bold text-foreground">{formatNationalPhone(phone)}</dd>
            </div>
            <div>
              <dt className="text-caption text-muted-foreground">{champs.motDePasse}</dt>
              <dd className="text-subtitle font-bold tracking-widest text-foreground">{formatPassword(password)}</dd>
            </div>
          </dl>
        </Card>
        <div className="flex flex-col gap-3">
          {done === 'sent' && (
            <Button icon={PawPrint} onClick={() => navigate(`/centres/${centerId}/ajouter`, { replace: true })}>
              {titres.ajouterSesAnimaux}
            </Button>
          )}
          <Button variant="secondary" icon={House} onClick={() => navigate('/', { replace: true })}>
            {mots.accueil}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{titres.inscrireEleveur}</h1>

      <Field label={champs.nomEleveur} required>
        <Input value={fullName} maxLength={120} autoComplete="off" onChange={(e) => setFullName(e.target.value)} />
      </Field>

      <Field label={champs.telephone} help={champs.telephoneAide} error={phoneError} required>
        <PhoneInput value={phone} onValueChange={setPhone} disabled={sending} />
      </Field>

      <Field label={champs.nomElevage} required>
        <Input value={centerName} maxLength={160} onChange={(e) => setCenterName(e.target.value)} />
      </Field>

      <Field label={champs.zone} required>
        <Select value={zoneId} onChange={(e) => setZoneId(e.target.value)} placeholder={champs.choisir} options={choices} />
      </Field>

      <ChoiceGrid
        multiple
        label={champs.especesElevees}
        value={speciesIds}
        onChange={setSpeciesIds}
        options={(species.data ?? []).map((s) => ({ value: s.id, label: s.label_fr, icon: speciesIcon(s.code) }))}
      />

      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        <Button icon={UserPlus} onClick={() => void send()} loading={sending}>
          {mots.inscrire}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)} disabled={sending}>
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
