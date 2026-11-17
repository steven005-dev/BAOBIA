/**
 * Fiche d'un animal ou d'un lot (gabarit Fiche détail) : identifiant très visible,
 * informations essentielles, action principale en bas (Transférer).
 * L'état sanitaire s'affichera quand le module santé le fournira.
 */

import { ArrowLeft, ArrowLeftRight, PawPrint } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { formatShortCode } from '@/lib/shortCode'
import { champs, messages, mots } from '@/lib/vocabulaire'

import { identityApi } from './api'
import { speciesIcon } from './speciesIcon'
import { useResource } from './useResource'

function Row({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-caption font-bold text-muted-foreground">{label}</dt>
      <dd className="text-body text-foreground">{value}</dd>
    </div>
  )
}

export function UnitPage() {
  const { unitId = '' } = useParams()
  const navigate = useNavigate()
  const { data: unit, error, loading } = useResource(() => identityApi.unit(unitId), unitId)

  if (loading) return <Loader />
  if (error?.kind === 'not_found') {
    return <EmptyState icon={PawPrint} title={messages.animalIntrouvable} />
  }
  if (error) return <Banner variant="error">{error.message}</Banner>
  if (!unit) return null

  const title = unit.kind === 'lot' ? mots.lot : mots.animal
  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)} className="self-start">
        {mots.retour}
      </Button>

      <div className="flex flex-col gap-1">
        <p className="text-caption font-bold text-muted-foreground">{title}</p>
        <h1 className="text-number font-bold tracking-wide text-foreground">
          {unit.label_code ? formatShortCode(unit.label_code) : unit.local_name ?? title}
        </h1>
      </div>

      <Card title={unit.species.label_fr} icon={speciesIcon(unit.species.code)}>
        <dl className="flex flex-col gap-4">
          <Row label={champs.nom} value={unit.local_name} />
          <Row label={champs.quantite} value={unit.lot?.current_size} />
          <Row label={mots.elevage} value={unit.current_center?.name} />
          <Row label={mots.etiquette} value={unit.label_code ? formatShortCode(unit.label_code) : null} />
          <Row label={champs.ajouteLe} value={new Date(unit.created_at).toLocaleDateString('fr-CI')} />
        </dl>
      </Card>

      <Button icon={ArrowLeftRight} onClick={() => navigate('/mouvements')}>
        {mots.transferer}
      </Button>
    </div>
  )
}
