/**
 * Remettre des étiquettes vierges à un élevage (agent de terrain, autorité).
 * On choisit l'élevage, on scanne ou saisit chaque étiquette, puis on envoie la liste.
 * Tout ou rien : si une étiquette est refusée, aucune n'est remise.
 */

import { ArrowLeft, CirclePlus, Send, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { CodeInput } from '@/components/CodeInput'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { formatShortCode, isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi } from './api'
import { QrScanner } from './QrScanner'
import { useResource } from './useResource'

export function IssueLabelsPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const centers = useResource(identityApi.centers, 'centres')
  const [centerId, setCenterId] = useState('')
  const [code, setCode] = useState('')
  const [codes, setCodes] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (centers.loading) return <Loader />
  if (centers.error) return <Banner variant="error">{centers.error.message}</Banner>
  const list = centers.data ?? []

  const add = (raw: string) => {
    const value = normalizeShortCode(raw)
    if (!isValidShortCode(value)) {
      setError(value.length === 9 ? erreurs.codeIncorrect : messages.etiquetteNonReconnue)
      return
    }
    if (codes.includes(value)) {
      setError(messages.etiquetteDejaDansLaListe)
      return
    }
    setError(null)
    setCodes((current) => [...current, value])
    setCode('')
  }

  const send = async () => {
    const target = centerId || list[0]?.id
    if (!target || codes.length === 0) {
      setError(messages.champManquant)
      return
    }
    setSending(true)
    setError(null)
    try {
      await identityApi.issueLabels(target, codes)
      toast.show(messages.etiquettesRemises, 'success')
      setCodes([])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{titres.remettreEtiquettes}</h1>

      {list.length === 0 ? (
        <EmptyState title={messages.aucunElevage} />
      ) : (
        <>
          <Field label={mots.elevage}>
            <Select
              value={centerId || list[0]?.id || ''}
              onChange={(e) => setCenterId(e.target.value)}
              options={list.map((c) => ({ value: c.id, label: c.name }))}
            />
          </Field>

          <QrScanner onCode={add} />
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              add(code)
            }}
          >
            <Field label={champs.codeEtiquette} help={champs.codeEtiquetteAide}>
              <CodeInput value={code} onValueChange={setCode} />
            </Field>
            <Button type="submit" variant="secondary" icon={CirclePlus} disabled={code.length !== 9}>
              {mots.ajouter}
            </Button>
          </form>

          {codes.length === 0 ? (
            <p className="text-body text-muted-foreground">{messages.aucuneEtiquette}</p>
          ) : (
            <ul className="flex flex-col gap-2" aria-label={mots.etiquettes}>
              {codes.map((c) => (
                <li key={c} className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-4 py-2">
                  <span className="text-body font-bold tracking-wide text-foreground">{formatShortCode(c)}</span>
                  <Button variant="ghost" icon={X} onClick={() => setCodes(codes.filter((x) => x !== c))}>
                    {mots.supprimer}
                  </Button>
                </li>
              ))}
            </ul>
          )}

          {error && <Banner variant="error">{error}</Banner>}

          <Button icon={Send} onClick={() => void send()} loading={sending} disabled={codes.length === 0}>
            {`${mots.envoyer} (${codes.length})`}
          </Button>
        </>
      )}

      <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)} disabled={sending}>
        {mots.retour}
      </Button>
    </div>
  )
}
