/**
 * Carte par zones (CA-01 à CA-04), sans fond de carte : elle s'affiche même sans réseau
 * vers un fournisseur de tuiles (fiche technique, section 11). Une tuile par zone.
 * Chaque état = couleur + contour sombre + icône + mot + MOTIF (charte, sections 2 et 11).
 * Aucun nom ni position d'élevage, sauf « Mes élevages ». Zone trop petite = grisée.
 */

import { Map as MapIcon, Warehouse } from 'lucide-react'
import { useState, type CSSProperties } from 'react'

import { Banner } from '@/components/Banner'
import { Card } from '@/components/Card'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { StatusBadge } from '@/components/StatusBadge'
import { healthApi, type ZoneState } from '@/features/health/api'
import { identityApi } from '@/features/identity/api'
import { speciesIcon } from '@/features/identity/speciesIcon'
import { useResource } from '@/features/identity/useResource'
import { HEALTH_STATE_ORDER, HEALTH_STATES, type HealthState } from '@/lib/healthStates'
import { carteTextes, champs } from '@/lib/vocabulaire'

/** Motifs de la charte (section 2), dessinés avec la couleur de contour de l'état. */
const PATTERNS: Record<HealthState, CSSProperties> = {
  normal: {},
  watch: { backgroundImage:
    'repeating-linear-gradient(0deg, transparent 0 7px, var(--health-watch-line) 7px 9px)' },
  exposure: { backgroundImage:
    'repeating-linear-gradient(45deg, transparent 0 7px, var(--health-exposure-line) 7px 10px)' },
  alert: { backgroundImage:
    'repeating-linear-gradient(0deg, transparent 0 4px, var(--health-alert-line) 4px 6px),' +
    'repeating-linear-gradient(90deg, transparent 0 4px, var(--health-alert-line) 4px 6px)' },
  unknown: { backgroundImage:
    'radial-gradient(var(--health-unknown-line) 2px, transparent 2.5px)', backgroundSize: '10px 10px' },
}

function ZoneTile({ zone, mine }: { zone: ZoneState; mine: string[] }) {
  const style = HEALTH_STATES[zone.state]
  return (
    <li className={`flex flex-col overflow-hidden rounded-lg border-4 bg-surface shadow-card ${style.classes}`}>
      <div aria-hidden className="h-12" style={PATTERNS[zone.state]} />
      <div className="flex flex-col gap-2 bg-surface p-3 text-foreground">
        <span className="text-card-title font-bold">{zone.zone.name}</span>
        <StatusBadge state={zone.state} className="self-start" />
        {!zone.is_masked && (
          <span className="text-small text-muted-foreground">
            {zone.centers_count} {carteTextes.elevagesDansZone} · {zone.animals_count} {carteTextes.animauxDansZone}
          </span>
        )}
        {mine.length > 0 && (
          <span className="inline-flex items-center gap-1 text-small font-bold">
            <Warehouse aria-hidden className="size-icon-small" /> {mine.join(', ')}
          </span>
        )}
      </div>
    </li>
  )
}

const ALL = 'all'

export function MapPage() {
  const [species, setSpecies] = useState<string>(ALL)
  const speciesList = useResource(identityApi.species, 'especes')
  const map = useResource(() => healthApi.map(species === ALL ? undefined : species), species)

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{carteTextes.titre}</h1>

      <ChoiceGrid
        label={champs.espece}
        value={species}
        onChange={setSpecies}
        options={[
          { value: ALL, label: carteTextes.toutesEspeces, icon: MapIcon },
          ...(speciesList.data ?? []).map((s) => ({ value: s.code, label: s.label_fr, icon: speciesIcon(s.code) })),
        ]}
      />

      <Card title={carteTextes.legende}>
        <ul className="flex flex-wrap gap-2">
          {HEALTH_STATE_ORDER.map((state) => (
            <li key={state} className="flex items-center gap-2">
              <span aria-hidden className={`size-8 rounded-sm border-2 ${HEALTH_STATES[state].classes}`}
                    style={PATTERNS[state]} />
              <StatusBadge state={state} />
            </li>
          ))}
        </ul>
        <p className="mt-2 text-caption text-muted-foreground">{carteTextes.pasDeNom}</p>
      </Card>

      {map.loading && <Loader />}
      {map.error && <Banner variant="error">{map.error.message}</Banner>}
      {map.data && map.data.zones.length === 0 && <EmptyState icon={MapIcon} title={carteTextes.aucuneZone} />}
      {map.data && map.data.zones.length > 0 && (
        <>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {map.data.zones.map((zone) => (
              <ZoneTile key={zone.zone.id} zone={zone}
                        mine={map.data!.my_centers.filter((c) => c.zone_id === zone.zone.id).map((c) => c.name)} />
            ))}
          </ul>
          <p className="text-caption text-muted-foreground">
            {carteTextes.majLe} {new Date(map.data.zones[0]?.computed_at ?? '').toLocaleString('fr-FR')}
          </p>
        </>
      )}
    </div>
  )
}
