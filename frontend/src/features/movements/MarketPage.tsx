/**
 * Marché (R2, spec v1.4 9.11 ; guide de réalisation des ajouts, 2 et 3).
 * L'agent ou le gestionnaire du marché choisit Entrée ou Sortie, puis scanne ou saisit
 * les animaux un à un : numéro de boucle RFID (15 chiffres) ou code BAOBIA.
 * Chaque scan part aussitôt par la file hors ligne ; la réponse du serveur colore la ligne :
 * vert (animal retrouvé), orange (avertissement ou refus), gris (inconnu, déjà scanné).
 * Un animal déclaré disparu donne un avertissement NEUTRE : ni « volé », ni propriétaire.
 */

import { useEffect, useRef, useState } from 'react'
import { BarChart3, KeyRound, LogIn, LogOut, Plus, Store, TriangleAlert } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { ApiError } from '@/lib/api'
import { isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { newUuid } from '@/lib/uuid'
import { erreurs } from '@/lib/vocabulaire'
import { submit } from '@/offline'

import type { Position } from '@/features/identity/api'
import { identityApi } from '@/features/identity/api'
import { currentPosition } from '@/features/identity/position'
import { QrScanner } from '@/features/identity/QrScanner'
import { useResource } from '@/features/identity/useResource'
import { subscribeOperation } from '@/features/offline/queue'

import { formatRfid, movementApi, normalizeRfid, type MarketScanResponse, type ResolvedDestination } from './api'

type Direction = 'in' | 'out'

interface ScanRow {
  id: string
  code: string
  status: 'pending' | 'sent' | 'check'
  response?: MarketScanResponse
  error?: string
  acknowledged?: boolean
}

/** Code scanné ou tapé -> numéro de boucle (15 chiffres) ou code BAOBIA ; null sinon. */
function cleanCode(raw: string): string | null {
  const rfid = normalizeRfid(raw)
  if (rfid) return rfid
  const short = normalizeShortCode(raw)
  return isValidShortCode(short) ? short : null
}

function displayCode(code: string) {
  return /^\d{15}$/.test(code) ? formatRfid(code) : code
}

function rowLook(row: ScanRow): { tone: string; text: string } {
  if (row.status === 'check') return { tone: 'border-destructive', text: row.error ?? 'À vérifier' }
  if (!row.response) return { tone: 'border-border text-muted-foreground', text: 'En attente d’envoi' }
  const { result, animal, warnings, reason } = row.response
  if (warnings[0]) return { tone: 'border-warning bg-warning-bg', text: warnings[0].message }
  if (result === 'ok') return { tone: 'border-success bg-success-bg', text: animal?.label ?? 'Animal retrouvé' }
  if (result === 'unknown') return { tone: 'border-border text-muted-foreground', text: 'Animal inconnu' }
  if (result === 'already_scanned') return { tone: 'border-border text-muted-foreground', text: 'Déjà scanné' }
  return { tone: 'border-warning bg-warning-bg', text: reason ?? 'Refusé' }
}

function vibrate(pattern: number) {
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) navigator.vibrate(pattern)
}

export function MarketPage() {
  const navigate = useNavigate()
  const centersResource = useResource(identityApi.centers, 'centres-marche')
  const markets = (centersResource.data ?? []).filter((center) => center.center_type === 'market')
  const [marketId, setMarketId] = useState('')
  const market = markets.find((item) => item.id === marketId) ?? markets[0]
  const [direction, setDirection] = useState<Direction>('in')
  const [rows, setRows] = useState<ScanRow[]>([])
  const [manualCode, setManualCode] = useState('')
  const [buyerCode, setBuyerCode] = useState('')
  const [buyer, setBuyer] = useState<ResolvedDestination | null>(null)
  const [buyerNote, setBuyerNote] = useState('')
  const [resolving, setResolving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const position = useRef<Position | null>(null)
  const unsubscribers = useRef(new Map<string, () => void>())

  useEffect(() => {
    void currentPosition().then((value) => { position.current = value })
    const subscriptions = unsubscribers.current
    return () => subscriptions.forEach((stop) => stop())
  }, [])

  if (centersResource.loading) return <Loader />
  if (centersResource.error) return <Banner variant="error">{centersResource.error.message}</Banner>
  if (!market) {
    return (
      <EmptyState icon={Store} title="Aucun marché"
                  text="Seul un membre d’un marché, ou un agent mandaté pour lui, peut enregistrer les entrées et sorties." />
    )
  }

  const follow = (id: string) => {
    const stop = subscribeOperation(id, (operation) => {
      if (!operation) return
      const status = operation.status === 'sending' ? 'pending' : operation.status
      const response = operation.response as MarketScanResponse | undefined
      setRows((current) => current.map((row) => row.id !== id ? row : {
        ...row, status, response: response ?? row.response, error: operation.last_error,
      }))
      if (status === 'sent' && response) vibrate(response.warnings.length ? 400 : 60)
      if (status !== 'pending') {
        stop()
        unsubscribers.current.delete(id)
      }
    })
    unsubscribers.current.set(id, stop)
  }

  const scan = async (raw: string) => {
    const code = cleanCode(raw)
    if (!code) {
      setError('Code non reconnu : 15 chiffres de la boucle, ou 9 caractères du code BAOBIA.')
      return
    }
    setError(null)
    setManualCode('')
    const id = newUuid()
    const where = position.current
    setRows((current) => [{ id, code, status: 'pending' }, ...current])
    try {
      await submit({
        id, type: 'market.scan', path: `/markets/${market.id}/scans/`, method: 'POST',
        body: {
          id, direction, code, scanned_at: new Date().toISOString(),
          ...(where ? { latitude: where.latitude, longitude: where.longitude,
                        position_accuracy_m: where.accuracy_m, position_source: 'gps' } : {}),
          ...(direction === 'out' ? { to_center_id: buyer?.center_id ?? null,
                                      to_party_note: buyer ? '' : buyerNote.trim() } : {}),
        },
      })
      follow(id)
    } catch (submitError) {
      setRows((current) => current.map((row) => row.id !== id ? row : {
        ...row, status: 'check', error: submitError instanceof ApiError ? submitError.message : erreurs.reseau,
      }))
    }
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

  const done = rows.filter((row) => row.response?.result === 'ok' && row.response.direction === direction).length
  const visible = rows.filter((row) => !row.response || row.response.direction === direction)

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-title font-bold text-foreground">Marché</h1>
      {markets.length > 1 ? (
        <Field label="Marché">
          <Select value={market.id} onChange={(event) => setMarketId(event.target.value)}
                  options={markets.map((item) => ({ value: item.id, label: item.name }))} />
        </Field>
      ) : (
        <p className="text-body font-bold text-foreground">{market.name}</p>
      )}

      <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Sens">
        {(['in', 'out'] as const).map((value) => (
          <Button key={value} role="radio" aria-checked={direction === value}
                  variant={direction === value ? 'primary' : 'secondary'}
                  icon={value === 'in' ? LogIn : LogOut} onClick={() => setDirection(value)}>
            {value === 'in' ? 'Entrée' : 'Sortie'}
          </Button>
        ))}
      </div>

      {direction === 'out' && (
        <section aria-labelledby="buyer-heading" className="flex flex-col gap-3 rounded-xl border-2 border-border p-4">
          <h2 id="buyer-heading" className="text-subtitle font-bold text-foreground">Acheteur (facultatif)</h2>
          {buyer ? (
            <Banner variant="success" title={buyer.center_name}
                    action={<Button variant="ghost" onClick={() => setBuyer(null)}>Changer</Button>}>
              Élevage inscrit : il confirmera la réception.
            </Banner>
          ) : (
            <>
              <Field label="Code partagé par l’élevage acheteur">
                <Input value={buyerCode} onChange={(event) => setBuyerCode(event.target.value)}
                       autoCapitalize="none" spellCheck={false} />
              </Field>
              <Button type="button" icon={KeyRound} variant="secondary" loading={resolving}
                      disabled={!buyerCode.trim()} onClick={() => void resolveBuyer()}>
                Vérifier l’élevage
              </Button>
              <Field label="Sinon, acheteur non inscrit" help="Nom ou lieu. Sans acheteur, l’animal sort du système.">
                <Input value={buyerNote} maxLength={160} onChange={(event) => setBuyerNote(event.target.value)} />
              </Field>
            </>
          )}
        </section>
      )}

      {error && <Banner variant="error">{error}</Banner>}
      <QrScanner onCode={(code) => void scan(code)} />
      <Field label="Numéro de boucle ou code" help="15 chiffres de la boucle, ou 9 caractères du code BAOBIA.">
        <Input value={manualCode} autoCapitalize="characters" spellCheck={false}
               onChange={(event) => setManualCode(event.target.value)}
               onKeyDown={(event) => { if (event.key === 'Enter') void scan(manualCode) }} />
      </Field>
      <Button type="button" icon={Plus} variant="secondary" disabled={!manualCode.trim()}
              onClick={() => void scan(manualCode)}>
        Ajouter
      </Button>

      <section aria-labelledby="scanned-heading" className="flex flex-col gap-2">
        <h2 id="scanned-heading" className="text-subtitle font-bold text-foreground">
          {done} animal{done > 1 ? 'aux' : ''} {direction === 'in' ? 'entré' : 'sorti'}{done > 1 ? 's' : ''}
        </h2>
        <ul className="flex flex-col gap-2">
          {visible.map((row) => {
            const look = rowLook(row)
            const warning = !!row.response?.warnings.length && !row.acknowledged
            return (
              <li key={row.id} className={`flex flex-col gap-2 rounded-lg border-2 px-4 py-3 ${look.tone}`}>
                <span className="text-body font-bold tracking-wide text-foreground">
                  {row.response?.animal?.tag ?? displayCode(row.code)}
                </span>
                <span className="inline-flex items-center gap-2 text-small text-foreground">
                  {row.response?.warnings.length ? <TriangleAlert aria-hidden className="size-icon-badge" /> : null}
                  {look.text}
                </span>
                {warning && (
                  <Button variant="secondary" onClick={() => setRows((current) => current.map((item) =>
                    item.id === row.id ? { ...item, acknowledged: true } : item))}>
                    J’ai compris
                  </Button>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <Button variant="ghost" icon={BarChart3} onClick={() => navigate(`/mouvements/marche/bilan?marche=${market.id}`)}>
        Bilan du jour
      </Button>
    </section>
  )
}
