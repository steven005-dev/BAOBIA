/**
 * Changer l'étiquette d'un animal ou d'un lot (spec 9.4) : une question, « Pourquoi ? »
 * (perdue, abîmée, mauvaise étiquette). Le nouveau code est CRÉÉ PAR LE TÉLÉPHONE ; la fiche
 * l'affiche ensuite pour faire la nouvelle étiquette. L'animal garde son identifiant ;
 * l'ancienne étiquette renverra vers lui (« étiquette remplacée » ou « perdue »).
 */

import { ArrowLeft, CircleHelp, CircleX, Pencil, QrCode } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { generateShortCode } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, type ReplaceReason } from './api'
import { LabelToPrint } from './LabelToPrint'

export function ReplaceLabelPage() {
  const { unitId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [reason, setReason] = useState<ReplaceReason | null>(null)
  const [code] = useState(generateShortCode)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [queued, setQueued] = useState(false)

  const send = async () => {
    if (!reason) {
      setError(messages.champManquant)
      return
    }
    setSending(true)
    setError(null)
    try {
      const result = await identityApi.replaceLabel(unitId, code, reason)
      if (result.status === 'sent') {
        toast.show(messages.etiquetteChangee, 'success')
        navigate(`/centres/animaux/${unitId}`, { replace: true })
      } else if (result.status === 'check') {
        setError(result.error ?? erreurs.saisie)
      } else {
        setQueued(true)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  if (queued) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-title font-bold text-foreground">{titres.changerEtiquette}</h1>
        <Banner variant="info" title={messages.enAttente}>
          {messages.gardeSurTelephone} {messages.etiquetteDejaImprimable}
        </Banner>
        <LabelToPrint code={code} species="" />
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)}>
          {mots.retour}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{titres.changerEtiquette}</h1>

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

      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        <Button icon={QrCode} onClick={() => void send()} loading={sending}>
          {mots.modifier}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} disabled={sending} onClick={() => navigate(-1)}>
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
