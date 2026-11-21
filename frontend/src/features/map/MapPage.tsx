/**
 * Carte sanitaire de Côte d'Ivoire (CA-01 à CA-04, Y3) : 14 districts, puis les régions
 * d'un district quand on le touche. Tracés dans l'application : marche hors ligne (PWA),
 * sans fournisseur de cartes. Chaque état = couleur + contour sombre + motif + mot.
 * Aucun nom d'élevage ; les points des élevages ne sont envoyés qu'au vétérinaire et à
 * l'Autorité (serveur). Sous la carte, la même information en liste (petit écran, lecteur d'écran).
 */

import { ArrowLeft, ArrowRight, Layers, Map as MapIcon, Route, Warehouse, ZoomIn } from 'lucide-react'
import { useMemo, useState, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { Loader } from '@/components/Loader'
import { StatusBadge } from '@/components/StatusBadge'
import { healthApi, type MapFlow, type ZoneState } from '@/features/health/api'
import { identityApi } from '@/features/identity/api'
import { speciesIcon } from '@/features/identity/speciesIcon'
import { useResource } from '@/features/identity/useResource'
import { HEALTH_STATE_ORDER, HEALTH_STATES, type HealthState } from '@/lib/healthStates'
import { formatShortCode } from '@/lib/shortCode'
import { carteTextes, champs, fluxTextes } from '@/lib/vocabulaire'

import { CiMap } from './CiMap'
import { FLOW_STYLE, SHAPES } from './shapes'

/** Motifs de la charte (section 2), pour la légende et la liste. */
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

const SEVERITY: Record<HealthState, number> = { alert: 0, exposure: 1, watch: 2, normal: 3, unknown: 4 }
const ALL = 'all'
const NAMES = new Map([...SHAPES.districts, ...SHAPES.regions].map((z) => [z.code, z.name]))
const DISTRICT_CODES = new Set(SHAPES.districts.map((z) => z.code))

function Swatch({ state }: { state: HealthState }) {
  return (
    <span aria-hidden className={`size-8 shrink-0 rounded-sm border-2 ${HEALTH_STATES[state].classes}`}
          style={PATTERNS[state]} />
  )
}

const FLOW_DAYS = [7, 30, 90, 365]

/** Trait d'exemple d'un flux (légende et fiche). */
function FlowSwatch({ confidence }: { confidence: MapFlow['confidence'] }) {
  const style = FLOW_STYLE[confidence]
  return (
    <svg aria-hidden viewBox="0 0 40 12" className="h-4 w-10 shrink-0">
      <path d="M2,6 H32" stroke={style.color} strokeWidth="3" strokeLinecap="round"
            strokeDasharray={style.dash?.split(' ').map((v) => Number(v) * 3).join(' ')} />
      <path d="M31,1 L39,6 L31,11 z" fill={style.color} />
    </svg>
  )
}

function day(iso: string) {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function FlowCard({ flow }: { flow: MapFlow }) {
  return (
    <Card title={`${fluxTextes.mouvementDu} ${day(flow.occurred_at)}`} icon={Route}>
      <p className="flex items-center gap-2 text-body font-bold">
        <FlowSwatch confidence={flow.confidence} /> {fluxTextes.confiance[flow.confidence]}
        <span className="font-normal text-muted-foreground">· {fluxTextes.types[flow.movement_type] ?? flow.movement_type}</span>
      </p>
      <div className="flex flex-wrap items-center gap-2 text-body">
        <span><span className="text-muted-foreground">{fluxTextes.de} </span><b>{flow.from.name}</b> ({flow.from.zone})</span>
        <ArrowRight aria-hidden className="size-icon-small" />
        <span><span className="text-muted-foreground">{fluxTextes.vers} </span><b>{flow.to.name}</b> ({flow.to.zone})</span>
      </div>
      <div>
        <p className="text-small font-bold">{fluxTextes.animaux} ({flow.count})</p>
        <ul className="mt-1 flex flex-col gap-1">
          {flow.animals.map((a, i) => {
            const Icon = speciesIcon(a.species)
            return (
              <li key={i} className="flex flex-wrap items-center gap-2 rounded-md bg-surface-secondary px-2 py-1 text-small">
                <Icon aria-hidden className="size-icon-small" />
                <span className="font-bold">{a.species_label}{a.kind === 'lot' ? ` × ${a.quantity}` : ''}</span>
                {a.local_name && <span>« {a.local_name} »</span>}
                {a.sex && fluxTextes.sexes[a.sex] && <span>{fluxTextes.sexes[a.sex]}</span>}
                <span className="font-mono">{a.code ? formatShortCode(a.code) : fluxTextes.sansEtiquette}</span>
              </li>
            )
          })}
        </ul>
      </div>
    </Card>
  )
}

function ZoneFacts({ zone }: { zone: ZoneState | undefined }) {
  if (!zone) return <p className="text-small text-muted-foreground">{carteTextes.aucunElevage}</p>
  if (zone.is_masked) return null
  return (
    <p className="text-small text-muted-foreground">
      {zone.centers_count} {carteTextes.elevagesDansZone} · {zone.animals_count} {carteTextes.animauxDansZone}
    </p>
  )
}

export function MapPage() {
  const [species, setSpecies] = useState<string>(ALL)
  const [level, setLevel] = useState<'districts' | 'regions'>('districts')
  // ?district=CI-D-… (depuis « Voir sur la carte » d'une alerte) : carte ouverte sur ce district.
  const [params] = useSearchParams()
  const initialDistrict = params.get('district')
  const startFocus = initialDistrict && DISTRICT_CODES.has(initialDistrict) ? initialDistrict : null
  const [focus, setFocus] = useState<string | null>(startFocus)
  const [selected, setSelected] = useState<string | null>(startFocus)
  const { hasRole } = useAuth()
  const professional = hasRole('veterinarian') || hasRole('authority')
  const [showFlows, setShowFlows] = useState(true)
  const [days, setDays] = useState(30)
  const [selectedFlow, setSelectedFlow] = useState<string | null>(null)
  const speciesList = useResource(identityApi.species, 'especes')
  const map = useResource(() => healthApi.map(species === ALL ? undefined : species), species)
  const flowsOn = professional && showFlows
  const flowsRes = useResource(
    () => healthApi.flows(days, species === ALL ? undefined : species),
    flowsOn ? `${days}-${species}` : null,
  )
  const flows = flowsOn ? (flowsRes.data?.flows ?? []) : []
  const currentFlow = flows.find((f) => f.id === selectedFlow)
  const selectFlow = (id: string) => {
    setSelectedFlow(id)
    setSelected(null)
  }

  const states = useMemo(
    () => new Map((map.data?.zones ?? []).map((z) => [z.zone.code, z] as const)),
    [map.data],
  )

  const onSelect = (code: string) => {
    setSelected(code)
    setSelectedFlow(null)
    // Toucher un district (vue du pays ou district voisin) : on zoome sur ses régions.
    if (DISTRICT_CODES.has(code) && level === 'districts') setFocus(code)
  }
  const backToCountry = () => {
    setFocus(null)
    setSelected(null)
  }

  // Zones listées sous la carte : celles qu'on voit, de la plus grave à la moins grave.
  const visibleCodes = focus
    ? SHAPES.regions.filter((r) => r.parent === focus).map((r) => r.code)
    : (level === 'regions' ? SHAPES.regions : SHAPES.districts).map((z) => z.code)
  const listed = visibleCodes
    .map((code) => ({ code, zone: states.get(code) }))
    .sort((a, b) => SEVERITY[a.zone?.state ?? 'unknown'] - SEVERITY[b.zone?.state ?? 'unknown'])
  const selectedZone = selected ? states.get(selected) : undefined
  const points = map.data?.points ?? []

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{carteTextes.titreCi}</h1>

      <ChoiceGrid
        label={champs.espece}
        value={species}
        onChange={setSpecies}
        options={[
          { value: ALL, label: carteTextes.toutesEspeces, icon: MapIcon },
          ...(speciesList.data ?? []).map((s) => ({ value: s.code, label: s.label_fr, icon: speciesIcon(s.code) })),
        ]}
      />

      {map.error && <Banner variant="error">{map.error.message}</Banner>}

      <div className="flex flex-col gap-4">
        <Card className="relative">
          <div className="flex flex-wrap items-center gap-2">
            {focus ? (
              <Button variant="secondary" icon={ArrowLeft} onClick={backToCountry}>
                {carteTextes.retourPays}
              </Button>
            ) : (
              <>
                <Button variant={level === 'districts' ? 'primary' : 'ghost'} icon={MapIcon}
                        aria-pressed={level === 'districts'}
                        onClick={() => { setLevel('districts'); setSelected(null) }}>
                  {carteTextes.districts} (14)
                </Button>
                <Button variant={level === 'regions' ? 'primary' : 'ghost'} icon={Layers}
                        aria-pressed={level === 'regions'}
                        onClick={() => { setLevel('regions'); setSelected(null) }}>
                  {carteTextes.regions} (31)
                </Button>
              </>
            )}
          </div>
          {professional && (
            <div className="flex flex-wrap items-center gap-2">
              <Button variant={showFlows ? 'primary' : 'ghost'} icon={Route} aria-pressed={showFlows}
                      onClick={() => { setShowFlows((v) => !v); setSelectedFlow(null) }}>
                {fluxTextes.afficher}
              </Button>
              {showFlows && (
                <div role="group" aria-label={fluxTextes.periode} className="flex flex-wrap gap-1">
                  {FLOW_DAYS.map((n) => (
                    <button key={n} type="button" aria-pressed={days === n}
                            onClick={() => { setDays(n); setSelectedFlow(null) }}
                            className={`min-h-11 rounded-md border-2 px-3 text-small font-bold ${days === n ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-surface text-foreground'}`}>
                      {fluxTextes.jours(n)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {map.loading && !map.data ? (
            <Loader />
          ) : (
            map.data && (
              <CiMap states={states} data={map.data} focus={focus} level={level}
                     selected={selected} onSelect={onSelect}
                     flows={flows} selectedFlow={selectedFlow} onSelectFlow={selectFlow} />
            )
          )}
          <p className="text-caption text-muted-foreground">{carteTextes.touchezZone}</p>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2">
          {currentFlow && <FlowCard flow={currentFlow} />}
          {selected && (
            <Card title={NAMES.get(selected) ?? selected}>
              <StatusBadge state={selectedZone?.state ?? 'unknown'} size="large" className="self-start" />
              <ZoneFacts zone={selectedZone} />
              {DISTRICT_CODES.has(selected) && focus !== selected && (
                <Button variant="secondary" icon={ZoomIn} onClick={() => setFocus(selected)}>
                  {carteTextes.voirRegions}
                </Button>
              )}
            </Card>
          )}

          <Card title={carteTextes.legende}>
            <ul className="flex flex-col gap-2">
              {HEALTH_STATE_ORDER.map((state) => (
                <li key={state} className="flex items-center gap-2">
                  <Swatch state={state} />
                  <StatusBadge state={state} />
                </li>
              ))}
              {points.length > 0 && (
                <>
                  <li className="flex items-center gap-2 text-small">
                    <svg aria-hidden viewBox="0 0 20 20" className="size-8"><circle cx="10" cy="10" r="6" fill="#17231B" stroke="#fff" strokeWidth="2" /></svg>
                    {carteTextes.pointElevage}
                  </li>
                  <li className="flex items-center gap-2 text-small">
                    <svg aria-hidden viewBox="0 0 20 20" className="size-8"><rect x="4" y="4" width="12" height="12" rx="2" fill="#17231B" stroke="#fff" strokeWidth="2" /></svg>
                    {carteTextes.pointMarche}
                  </li>
                  <li className="flex items-center gap-2 text-small">
                    <svg aria-hidden viewBox="0 0 20 20" className="size-8"><circle cx="10" cy="10" r="9" fill="#17231B" /><text x="10" y="11" textAnchor="middle" dominantBaseline="middle" fontSize="9" fill="#fff" fontWeight="700">3</text></svg>
                    {carteTextes.pointGroupe}
                  </li>
                </>
              )}
              {flows.length > 0 && (Object.keys(fluxTextes.confiance) as MapFlow['confidence'][]).map((c) => (
                <li key={c} className="flex items-center gap-2 text-small">
                  <FlowSwatch confidence={c} /> {fluxTextes.confiance[c]}
                </li>
              ))}
              {(map.data?.my_centers ?? []).some((c) => c.latitude) && (
                <li className="flex items-center gap-2 text-small">
                  <svg aria-hidden viewBox="0 0 20 20" className="size-8"><circle cx="10" cy="10" r="7" fill="var(--focus)" stroke="#fff" strokeWidth="2.5" /></svg>
                  {carteTextes.mesElevages}
                </li>
              )}
            </ul>
            <p className="mt-2 text-caption text-muted-foreground">
              {carteTextes.pasDeNom} {points.length > 0 && carteTextes.pointsReserves}
            </p>
          </Card>
        </div>
      </div>

      {flowsOn && (
        <section className="flex flex-col gap-3" aria-label={fluxTextes.liste}>
          <h2 className="text-subtitle font-bold text-foreground">{fluxTextes.liste} ({flows.length})</h2>
          {flowsRes.data && flows.length === 0 && <p className="text-body text-muted-foreground">{fluxTextes.aucun}</p>}
          <ul className="flex flex-col gap-2">
            {flows.map((f) => (
              <li key={f.id}>
                <button type="button" onClick={() => selectFlow(f.id)}
                        className={`flex w-full flex-wrap items-center gap-2 rounded-lg border-2 bg-surface px-3 py-2 text-left text-small ${selectedFlow === f.id ? 'border-focus' : 'border-border'}`}>
                  <FlowSwatch confidence={f.confidence} />
                  <span className="font-bold">{day(f.occurred_at)}</span>
                  <span>{f.from.name}</span><ArrowRight aria-hidden className="size-icon-small" /><span>{f.to.name}</span>
                  <span className="text-muted-foreground">· {f.count} {f.animals[0]?.species_label.toLowerCase()}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="flex flex-col gap-3" aria-label={carteTextes.listeZones}>
        <h2 className="text-subtitle font-bold text-foreground">{carteTextes.listeZones}</h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {listed.map(({ code, zone }) => {
            const state = zone?.state ?? 'unknown'
            const mine = (map.data?.my_centers ?? []).filter((c) => zone && c.zone_id === zone.zone.id)
            return (
              <li key={code}>
                <button type="button" onClick={() => onSelect(code)}
                        className={`flex w-full flex-col overflow-hidden rounded-lg border-4 bg-surface text-left shadow-card ${HEALTH_STATES[state].classes} ${selected === code ? 'ring-4 ring-focus' : ''}`}>
                  <span aria-hidden className="h-8 w-full" style={PATTERNS[state]} />
                  <span className="flex flex-col gap-2 bg-surface p-3 text-foreground">
                    <span className="text-card-title font-bold">{NAMES.get(code)}</span>
                    <StatusBadge state={state} className="self-start" />
                    <ZoneFacts zone={zone} />
                    {mine.length > 0 && (
                      <span className="inline-flex items-center gap-1 text-small font-bold">
                        <Warehouse aria-hidden className="size-icon-small" /> {mine.map((c) => c.name).join(', ')}
                      </span>
                    )}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
        <p className="text-caption text-muted-foreground">
          {map.data?.zones[0] && `${carteTextes.majLe} ${new Date(map.data.zones[0].computed_at).toLocaleString('fr-FR')} · `}
          {carteTextes.sourceTraces}
        </p>
      </section>
    </div>
  )
}
