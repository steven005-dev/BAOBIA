/**
 * Marché (R2, spec v1.4 9.11) : l'agent ou le gestionnaire du marché scanne les animaux
 * qui ENTRENT et qui SORTENT, plusieurs à la suite. Une seule action par écran.
 * - Entrée : déclarée par le marché seul, sans code ; « probable » tant que l'élevage
 *   d'origine ne confirme pas.
 * - Sortie : vers un élevage inscrit (code de confirmation à transmettre) ou vers un
 *   acheteur non inscrit (l'animal sort du système).
 * Tout passe par la file hors ligne ; les codes scannés sont résolus par le serveur.
 */

import { useEffect, useState } from 'react'
import { ArrowLeft, KeyRound, LogIn, LogOut, Pencil, Plus, Store, Trash2 } from 'lucide-react'

import { Banner } from '@/components/Banner'
import { BigChoiceTile } from '@/components/BigChoiceTile'
import { Button } from '@/components/Button'
import { CodeInput } from '@/components/CodeInput'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { SyncStatusBanner } from '@/components/SyncStatusBanner'
import { ApiError } from '@/lib/api'
import { isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { newUuid } from '@/lib/uuid'
import { erreurs } from '@/lib/vocabulaire'
import { submit, type OperationStatus } from '@/offline'

import { identityApi } from '@/features/identity/api'
import { QrScanner } from '@/features/identity/QrScanner'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'

import { movementApi, type ResolvedDestination } from './api'

type Direction = 'entry' | 'exit'

const TITLES: Record<Direction, string> = { entry: 'Entrée au marché', exit: 'Sortie du marché' }

export function MarketPage() {
  const centersResource = useResource(identityApi.centers, 'centres-marche')
  const markets = (centersResource.data ?? []).filter((center) => center.center_type === 'market')
  const [marketId, setMarketId] = useState('')
  const market = markets.find((item) => item.id === marketId) ?? markets[0]
  const [direction, setDirection] = useState<Direction | null>(null)
  const [codes, setCodes] = useState<string[]>([])
  const [manualCode, setManualCode] = useState('')
  const [buyerCode, setBuyerCode] = useState('')
  const [buyer, setBuyer] = useState<ResolvedDestination | null>(null)
  const [buyerNote, setBuyerNote] = useState('')
  const [resolving, setResolving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [operationId, setOperationId] = useState<string | null>(null)
  const [operationStatus, setOperationStatus] = useState<OperationStatus>('pending')
  const [confirmationCode, setConfirmationCode] = useState<string | null>(null)

  useEffect(() => {
    if (!operationId) return
    return subscribeOperation(operationId, (operation) => {
      if (!operation) return
      setOperationStatus(operation.status === 'sending' ? 'pending' : operation.status)
      if (operation.status === 'check') setError(operation.last_error ?? erreurs.saisie)
      const response = operation.response as { confirmation_code?: string | null } | undefined
      if (response?.confirmation_code) setConfirmationCode(response.confirmation_code)
    })
  }, [operationId])

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (!market) {
    return (
      <EmptyState icon={Store} title="Aucun marché"
                  text="Seul un membre d’un marché, ou un agent mandaté pour lui, peut enregistrer les entrées et sorties." />
    )
  }

  const reset = (keepDirection = false) => {
    setCodes([])
    setManualCode('')
    setBuyer(null)
    setBuyerCode('')
    setBuyerNote('')
    setError(null)
    setOperationId(null)
    setOperationStatus('pending')
    setConfirmationCode(null)
    if (!keepDirection) setDirection(null)
  }

  const addCode = (raw: string) => {
    const code = normalizeShortCode(raw)
    if (!isValidShortCode(code)) {
      setError(erreurs.codeIncorrect)
      return
    }
    setError(null)
    setCodes((current) => (current.includes(code) ? current : [...current, code]))
    setManualCode('')
  }

  const resolveBuyer = async () => {
    setResolving(true)
    setError(null)
    try {
      setBuyer(await movementApi.resolveDestinationCode(buyerCode.trim()))
    } catch (resolveError) {
      setError(resolveError instanceof ApiError ? resolveError.message : erreurs.reseau)
    } finally {
      setResolving(false)
    }
  }

  if (operationId && direction) {
    return (
      <section className="flex flex-col gap-5 rounded-xl border-2 border-border bg-surface p-5 shadow-card">
        <h1 className="text-title font-bold text-foreground">{TITLES[direction]}</h1>
        <SyncStatusBanner status={operationStatus} />
        {operationStatus === 'check' && error && <Banner variant="error">{error}</Banner>}
        {operationStatus === 'sent' && direction === 'entry' && (
          <Banner variant="success" title="Entrée enregistrée.">
            Les animaux comptent au marché. Le mouvement reste « probable » tant que l’élevage d’origine ne le confirme pas.
          </Banner>
        )}
        {operationStatus === 'sent' && direction === 'exit' && !buyer && (
          <Banner variant="success" title="Sortie enregistrée.">
            L’acheteur n’est pas inscrit : les animaux sortent du système. Ils restent dans l’historique.
          </Banner>
        )}
        {direction === 'exit' && buyer && confirmationCode && (
          <Banner variant="info" title="Code de confirmation à transmettre">
            <span className="text-title font-bold tracking-widest">{confirmationCode}</span>
            <br />À donner à l’acheteur ({buyer.center_name}) pour qu’il confirme la réception.
          </Banner>
        )}
        <Button icon={direction === 'entry' ? LogIn : LogOut} fullWidth onClick={() => reset(true)}>
          {direction === 'entry' ? 'Nouvelle entrée' : 'Nouvelle sortie'}
        </Button>
        <Button variant="ghost" icon={ArrowLeft} onClick={() => reset()}>Retour au marché</Button>
      </section>
    )
  }

  if (!direction) {
    return (
      <section className="flex flex-col gap-6">
        <h1 className="text-title font-bold text-foreground">Marché</h1>
        {markets.length > 1 ? (
          <Field label="Marché">
            <Select value={market.id} onChange={(event) => setMarketId(event.target.value)}
                    options={markets.map((item) => ({ value: item.id, label: item.name }))} />
          </Field>
        ) : (
          <p className="text-body font-bold text-foreground">{market.name}</p>
        )}
        <div className="grid grid-cols-2 gap-4">
          <BigChoiceTile icon={LogIn} label="Entrée" description="Animaux qui arrivent"
                         onClick={() => setDirection('entry')} />
          <BigChoiceTile icon={LogOut} label="Sortie" description="Animaux qui partent"
                         onClick={() => setDirection('exit')} />
        </div>
      </section>
    )
  }

  const canSend = codes.length > 0 && (direction === 'entry' || !!buyer || !!buyerNote.trim())

  const send = async () => {
    if (!canSend) {
      setError(erreurs.saisie)
      return
    }
    const id = newUuid()
    const occurredAt = new Date().toISOString()
    setSaving(true)
    setError(null)
    try {
      await submit({
        id,
        type: direction === 'entry' ? 'market.entry' : 'market.exit',
        path: direction === 'entry' ? '/market/entries/' : '/market/exits/',
        method: 'POST',
        body: direction === 'entry'
          ? { id, market_id: market.id, label_codes: codes, occurred_at: occurredAt }
          : { id, market_id: market.id, label_codes: codes, occurred_at: occurredAt,
              to_center_id: buyer?.center_id ?? null, to_party_note: buyer ? '' : buyerNote.trim() },
      })
      setOperationId(id)
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : erreurs.reseau)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{TITLES[direction]}</h1>
      <p className="text-body text-muted-foreground">{market.name} · scannez les étiquettes une à une.</p>
      {error && <Banner variant="error">{error}</Banner>}

      <QrScanner onCode={addCode} />
      <Field label="Ou saisir le code de l’étiquette">
        <CodeInput value={manualCode} onValueChange={setManualCode} />
      </Field>
      <Button type="button" icon={Plus} variant="secondary" disabled={manualCode.length < 9}
              onClick={() => addCode(manualCode)}>
        Ajouter
      </Button>

      <section aria-labelledby="scanned-heading" className="flex flex-col gap-2">
        <h2 id="scanned-heading" className="text-subtitle font-bold text-foreground">
          {codes.length} animal{codes.length > 1 ? 'aux' : ''} scanné{codes.length > 1 ? 's' : ''}
        </h2>
        <ul className="flex flex-col gap-2">
          {codes.map((code) => (
            <li key={code} className="flex items-center justify-between rounded-lg border-2 border-border bg-surface px-4 py-2">
              <span className="text-body font-bold tracking-widest text-foreground">{code}</span>
              <Button type="button" variant="ghost" icon={Trash2}
                      onClick={() => setCodes((current) => current.filter((item) => item !== code))}>
                Retirer
              </Button>
            </li>
          ))}
        </ul>
      </section>

      {direction === 'exit' && (
        <section aria-labelledby="buyer-heading" className="flex flex-col gap-3">
          <h2 id="buyer-heading" className="text-subtitle font-bold text-foreground">Acheteur</h2>
          {buyer ? (
            <Banner variant="success" title={buyer.center_name}
                    action={<Button variant="ghost" icon={Pencil} onClick={() => setBuyer(null)}>Changer</Button>}>
              Élevage inscrit : il confirmera avec le code.
            </Banner>
          ) : (
            <>
              <Field label="Code partagé par l’élevage acheteur" help="S’il a BAOBIA, il le montre depuis « Partager mon élevage ».">
                <Input value={buyerCode} onChange={(event) => setBuyerCode(event.target.value)}
                       autoCapitalize="none" spellCheck={false} />
              </Field>
              <Button type="button" icon={KeyRound} variant="secondary" loading={resolving}
                      disabled={!buyerCode.trim()} onClick={() => void resolveBuyer()}>
                Vérifier l’élevage
              </Button>
              <Field label="Sinon, acheteur non inscrit" help="Nom ou lieu, par exemple « Acheteur de Bouaké ». Les animaux sortiront du système.">
                <Input value={buyerNote} maxLength={160} onChange={(event) => setBuyerNote(event.target.value)} />
              </Field>
            </>
          )}
        </section>
      )}

      <Button icon={direction === 'entry' ? LogIn : LogOut} fullWidth loading={saving} disabled={!canSend}
              onClick={() => void send()}>
        {direction === 'entry' ? 'Enregistrer l’entrée' : 'Enregistrer la sortie'}
      </Button>
      <Button variant="ghost" icon={ArrowLeft} onClick={() => reset()}>Retour</Button>
    </section>
  )
}
