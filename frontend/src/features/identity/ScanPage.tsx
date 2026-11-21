/**
 * Scanner : retrouver un animal par son étiquette (caméra ou code saisi).
 * Animal dans mes élevages (ou ma zone pour un vétérinaire) : on ouvre sa fiche.
 * Sinon : vue réduite (espèce seulement), aucun nom d'élevage.
 */

import { Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { Input } from '@/components/Input'
import { Field } from '@/components/Field'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { normalizeRfid } from '@/features/movements/api'
import { formatShortCode, isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots } from '@/lib/vocabulaire'

import { identityApi, type ScanResult } from './api'
import { currentPosition } from './position'
import { QrScanner } from './QrScanner'
import { speciesIcon } from './speciesIcon'

const RESULT_MESSAGES: Record<ScanResult['result'], string> = {
  found: messages.scanReussi,
  replaced: messages.etiquetteRemplacee,
  lost: messages.etiquettePerdue,
}

export function ScanPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reduced, setReduced] = useState<ScanResult | null>(null)

  const lookup = async (raw: string, method: 'scan' | 'manual_code') => {
    // Identifiant officiel (21/11) : 15 chiffres de la boucle ; sinon code BAOBIA (9 caractères).
    const official = normalizeRfid(raw)
    const value = official ?? normalizeShortCode(raw)
    setCode(official ? raw : value)
    setReduced(null)
    if (!official && !isValidShortCode(value)) {
      setError(value.length === 9 ? erreurs.codeIncorrect : messages.etiquetteNonReconnue)
      return
    }
    setError(null)
    setBusy(true)
    try {
      const result = await identityApi.scan(value)
      if (result.full_access && result.unit) {
        const unitId = result.unit.id
        // Trace du contrôle, sans bloquer l'écran (la position peut prendre quelques secondes).
        const labelCode = result.label_code
        if (labelCode) {
          void currentPosition()
            .then((position) => identityApi.recordVerification(unitId, labelCode, method, position))
            .catch(() => {})
        }
        toast.show(RESULT_MESSAGES[result.result], result.result === 'found' ? 'success' : 'warning')
        navigate(`/centres/animaux/${result.unit.id}`)
      } else {
        setReduced(result)
      }
    } catch (err) {
      if (err instanceof ApiError && err.kind === 'validation') setError(messages.etiquetteNonReconnue)
      else if (err instanceof ApiError && err.kind === 'not_found') setError(messages.animalIntrouvable)
      else setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setBusy(false)
    }
  }

  const isOfficial = normalizeRfid(code) !== null
  const codeError = !isOfficial && code.length === 9 && !isValidShortCode(normalizeShortCode(code))
    ? erreurs.codeIncorrect : null

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{mots.scanner}</h1>

      <QrScanner onCode={(value) => void lookup(value, 'scan')} />

      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          void lookup(code, 'manual_code')
        }}
      >
        <Field label={champs.numeroOuCode} help={champs.numeroOuCodeAide} error={codeError}>
          <Input value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" />
        </Field>
        <Button type="submit" variant="secondary" icon={Search} loading={busy}
                disabled={!isOfficial && normalizeShortCode(code).length !== 9}>
          {mots.rechercher}
        </Button>
      </form>

      {error && <Banner variant="error">{error}</Banner>}

      {reduced && (
        <Card title={reduced.species.label_fr} icon={speciesIcon(reduced.species.code)}>
          {reduced.label_code && <p className="text-body text-foreground">{formatShortCode(reduced.label_code)}</p>}
          <p className="text-body text-muted-foreground">
            {reduced.result === 'found' ? messages.pasDansVosElevages : RESULT_MESSAGES[reduced.result]}
          </p>
        </Card>
      )}
    </div>
  )
}
