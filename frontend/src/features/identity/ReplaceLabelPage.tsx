/**
 * Changer l'étiquette d'un animal ou d'un lot (spec 9.4) : deux questions.
 * 1. Pourquoi ? (perdue, abîmée, mauvaise étiquette)  2. La nouvelle étiquette.
 * L'animal garde son identifiant ; l'ancienne étiquette renverra « étiquette remplacée ».
 */

import { ArrowLeft, ArrowRight, CircleHelp, CircleX, Pencil, QrCode } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { CodeInput } from '@/components/CodeInput'
import { Field } from '@/components/Field'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { isValidShortCode, normalizeShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, type ReplaceReason } from './api'
import { QrScanner } from './QrScanner'

export function ReplaceLabelPage() {
  const { unitId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [step, setStep] = useState<1 | 2>(1)
  const [reason, setReason] = useState<ReplaceReason | null>(null)
  const [code, setCode] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = async () => {
    if (!reason || !isValidShortCode(code)) {
      setError(code.length === 9 ? erreurs.codeIncorrect : messages.champManquant)
      return
    }
    setSending(true)
    setError(null)
    try {
      await identityApi.replaceLabel(unitId, code, reason)
      toast.show(messages.etiquetteChangee, 'success')
      navigate(`/centres/animaux/${unitId}`, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  const next = () => {
    if (!reason) {
      setError(messages.champManquant)
      return
    }
    setError(null)
    setStep(2)
  }

  const codeError = code.length === 9 && !isValidShortCode(code) ? erreurs.codeIncorrect : null

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <p className="text-caption font-bold text-muted-foreground">
          {champs.etape} {step} {champs.sur} 2
        </p>
        <h1 className="text-title font-bold text-foreground">{titres.changerEtiquette}</h1>
      </div>

      {step === 1 && (
        <ChoiceGrid
          label={titres.pourquoiChanger}
          value={reason}
          onChange={(value) => setReason(value as ReplaceReason)}
          options={[
            { value: 'lost', label: champs.etiquettePerdue, icon: CircleHelp },
            { value: 'damaged', label: champs.etiquetteAbimee, icon: CircleX },
            { value: 'error', label: champs.mauvaiseEtiquette, icon: Pencil },
          ]}
        />
      )}

      {step === 2 && (
        <div className="flex flex-col gap-4">
          <h2 className="text-subtitle font-bold text-foreground">{titres.nouvelleEtiquette}</h2>
          <QrScanner onCode={(value) => setCode(normalizeShortCode(value))} />
          <Field label={champs.codeEtiquette} help={champs.codeEtiquetteAide} error={codeError}>
            <CodeInput value={code} onValueChange={setCode} />
          </Field>
        </div>
      )}

      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        {step === 1 ? (
          <Button icon={ArrowRight} onClick={next}>
            {mots.continuer}
          </Button>
        ) : (
          <Button icon={QrCode} onClick={() => void send()} loading={sending}>
            {mots.modifier}
          </Button>
        )}
        <Button
          variant="secondary"
          icon={ArrowLeft}
          disabled={sending}
          onClick={() => (step === 2 ? setStep(1) : navigate(-1))}
        >
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
