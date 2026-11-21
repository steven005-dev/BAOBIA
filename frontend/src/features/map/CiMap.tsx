/**
 * Carte de Côte d'Ivoire en SVG (d3-geo), SANS fond de carte : les tracés des 14 districts
 * et des 33 régions (31 régions + 2 districts autonomes) sont dans l'application
 * (ci-zones.json, geoBoundaries CC BY 4.0), donc la carte marche hors ligne (PWA).
 *
 * - Vue du pays : les districts, colorés selon leur état. Toucher un district = zoom sur ses régions.
 * - Chaque état = couleur + contour sombre + motif (charte) ; le mot est dans la légende et la fiche.
 * - Points des élevages : seulement ceux que le serveur renvoie (vétérinaire, autorité),
 *   regroupés en ronds numérotés quand ils sont proches ; « Mes élevages » en bleu.
 */

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import type { FlowConfidence, MapData, MapFlow, ZoneState } from '@/features/health/api'
import { HEALTH_STATE_ORDER, HEALTH_STATES, type HealthState } from '@/lib/healthStates'

import { boxFor, FLOW_STYLE, FULL, SHAPES, WIDTH, type ViewBox } from './shapes'

/** viewBox animé (400 ms) : on voit le zoom se faire. */
function useAnimatedBox(target: ViewBox) {
  const [box, setBox] = useState<ViewBox>(target)
  const from = useRef<ViewBox>(target)
  useEffect(() => {
    const start = performance.now()
    const origin = from.current
    let frame = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 400)
      const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2
      const next = origin.map((v, i) => v + ((target[i] ?? v) - v) * e) as ViewBox
      from.current = next
      setBox(next)
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target])
  return box
}

interface Cluster {
  x: number
  y: number
  count: number
  market: boolean
}

function clusterPoints(points: [number, number, boolean][], cell: number): Cluster[] {
  const groups = new Map<string, Cluster & { sx: number; sy: number }>()
  for (const [x, y, market] of points) {
    const key = `${Math.floor(x / cell)}:${Math.floor(y / cell)}`
    const g = groups.get(key)
    if (g) {
      g.count += 1
      g.sx += x
      g.sy += y
      g.market = g.market && market
    } else {
      groups.set(key, { x, y, sx: x, sy: y, count: 1, market })
    }
  }
  return [...groups.values()].map((g) => ({ x: g.sx / g.count, y: g.sy / g.count, count: g.count, market: g.market }))
}

export interface CiMapProps {
  /** États par code de zone (CI-D-..., CI-R-...). */
  states: Map<string, ZoneState>
  data: MapData
  /** District zoomé (ses régions sont colorées), ou null pour tout le pays. */
  focus: string | null
  /** Vue du pays : 'districts' (14) ou 'regions' (33). */
  level: 'districts' | 'regions'
  selected: string | null
  onSelect: (code: string) => void
  /** Flux des animaux (vétérinaire, autorité) ; vide = rien n'est dessiné. */
  flows?: MapFlow[]
  selectedFlow?: string | null
  onSelectFlow?: (id: string) => void
}

export function CiMap({ states, data, focus, level, selected, onSelect, flows = [], selectedFlow = null,
                        onSelectFlow }: CiMapProps) {
  const focusShape = focus ? SHAPES.districts.find((z) => z.code === focus) : undefined
  const target = useMemo(() => (focusShape ? boxFor(focusShape.bounds) : FULL), [focusShape])
  const box = useAnimatedBox(target)
  const k = box[2] / WIDTH // 1 = tout le pays ; plus petit = zoomé

  const showRegions = Boolean(focus) || level === 'regions'
  const colored = showRegions
    ? SHAPES.regions.filter((r) => !focus || r.parent === focus)
    : SHAPES.districts
  const background = focus ? SHAPES.districts.filter((d) => d.code !== focus) : []

  const projected = useMemo(() => {
    const project = (lat: string | null, lon: string | null) =>
      lat && lon ? SHAPES.projection([Number(lon), Number(lat)]) : null
    const points = (data.points ?? [])
      .map((p) => {
        const xy = project(p.latitude, p.longitude)
        return xy ? ([xy[0], xy[1], p.type === 'market'] as [number, number, boolean]) : null
      })
      .filter((p): p is [number, number, boolean] => p !== null)
    const mine = data.my_centers
      .map((c) => project(c.latitude, c.longitude))
      .filter((p): p is [number, number] => p !== null)
    return { points, mine }
  }, [data])
  const clusters = clusterPoints(projected.points, 26 * k)

  // Flux : courbe de l'origine à la destination ; plusieurs flux entre les mêmes lieux s'écartent.
  const drawnFlows = useMemo(() => {
    const seen = new Map<string, number>()
    return flows.flatMap((f) => {
      const a = f.from.latitude && f.from.longitude ? SHAPES.projection([Number(f.from.longitude), Number(f.from.latitude)]) : null
      const b = f.to.latitude && f.to.longitude ? SHAPES.projection([Number(f.to.longitude), Number(f.to.latitude)]) : null
      if (!a || !b) return []
      const key = `${a[0].toFixed(0)}:${a[1].toFixed(0)}>${b[0].toFixed(0)}:${b[1].toFixed(0)}`
      const n = seen.get(key) ?? 0
      seen.set(key, n + 1)
      const [dx, dy] = [b[0] - a[0], b[1] - a[1]]
      const bend = 0.22 + 0.12 * n
      const c: [number, number] = [(a[0] + b[0]) / 2 - dy * bend, (a[1] + b[1]) / 2 + dx * bend]
      return [{ flow: f, d: `M${a[0]},${a[1]} Q${c[0]},${c[1]} ${b[0]},${b[1]}` }]
    })
  }, [flows])

  const stateOf = (code: string): HealthState => states.get(code)?.state ?? 'unknown'
  const keyHandler = (code: string) => (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(code)
    }
  }

  return (
    <svg
      viewBox={box.join(' ')}
      className="h-auto w-full touch-manipulation select-none rounded-lg border border-border bg-[#EAF2F7]"
      role="group"
      aria-label="Carte de Côte d'Ivoire"
    >
      <defs>
        {HEALTH_STATE_ORDER.map((state) => (
          <pattern key={state} id={`motif-${state}`} patternUnits="userSpaceOnUse"
                   width={10 * k} height={10 * k}>
            {state === 'watch' && <rect y={7 * k} width={10 * k} height={1.6 * k} fill="var(--health-watch-line)" />}
            {state === 'exposure' && (
              <path d={`M0 ${10 * k} L${10 * k} 0`} stroke="var(--health-exposure-line)" strokeWidth={2 * k} />
            )}
            {state === 'alert' && (
              <path d={`M0 ${5 * k} H${10 * k} M${5 * k} 0 V${10 * k}`} stroke="var(--health-alert-line)"
                    strokeWidth={1.5 * k} />
            )}
            {state === 'unknown' && <circle cx={5 * k} cy={5 * k} r={1.6 * k} fill="var(--health-unknown-line)" />}
          </pattern>
        ))}
      </defs>

      {/* districts voisins, en retrait quand on est zoomé */}
      {background.map((z) => (
        <path key={z.code} d={z.d} fill={`var(--health-${stateOf(z.code)})`} opacity={0.25}
              stroke="#FFFFFF" strokeWidth={1.2 * k} onClick={() => onSelect(z.code)} />
      ))}

      {colored.map((z) => {
        const state = stateOf(z.code)
        const isSelected = selected === z.code
        return (
          <g key={z.code} role="button" tabIndex={0} aria-label={`${z.name} : ${HEALTH_STATES[state].label}`}
             aria-pressed={isSelected} className="cursor-pointer outline-none"
             onClick={() => onSelect(z.code)} onKeyDown={keyHandler(z.code)}>
            <title>{`${z.name} : ${HEALTH_STATES[state].label}`}</title>
            <path d={z.d} fill={`var(--health-${state})`} />
            {state !== 'normal' && <path d={z.d} fill={`url(#motif-${state})`} />}
            <path d={z.d} fill="none" stroke={isSelected ? 'var(--focus)' : `var(--health-${state}-line)`}
                  strokeWidth={(isSelected ? 4 : 1.4) * k} strokeLinejoin="round" />
          </g>
        )
      })}

      {/* frontières blanches fines par-dessus, pour bien séparer les zones */}
      {colored.map((z) => (
        <path key={`b-${z.code}`} d={z.d} fill="none" stroke="#FFFFFF" strokeOpacity={0.7}
              strokeWidth={0.6 * k} pointerEvents="none" />
      ))}

      {/* points des élevages (vétérinaire, autorité) */}
      {clusters.map((c, i) =>
        c.count === 1 ? (
          c.market ? (
            <rect key={i} x={c.x - 5 * k} y={c.y - 5 * k} width={10 * k} height={10 * k} rx={1.5 * k}
                  fill="#17231B" stroke="#FFFFFF" strokeWidth={1.8 * k} pointerEvents="none" />
          ) : (
            <circle key={i} cx={c.x} cy={c.y} r={6 * k} fill="#17231B" stroke="#FFFFFF"
                    strokeWidth={1.8 * k} pointerEvents="none" />
          )
        ) : (
          <g key={i} pointerEvents="none">
            <circle cx={c.x} cy={c.y} r={(9 + Math.min(6, Math.log2(c.count) * 2)) * k} fill="#17231B"
                    stroke="#FFFFFF" strokeWidth={2 * k} />
            <text x={c.x} y={c.y} textAnchor="middle" dominantBaseline="central" fontSize={10 * k}
                  fontWeight={700} fill="#FFFFFF">{c.count}</text>
          </g>
        ),
      )}

      {/* flux des animaux */}
      {drawnFlows.length > 0 && (
        <defs>
          {(Object.keys(FLOW_STYLE) as FlowConfidence[]).map((conf) => (
            <marker key={conf} id={`fleche-${conf}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4"
                    markerHeight="4" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill={FLOW_STYLE[conf].color} />
            </marker>
          ))}
        </defs>
      )}
      {drawnFlows.map(({ flow, d }) => {
        const style = FLOW_STYLE[flow.confidence]
        const width = (2.2 + Math.min(4, flow.count * 0.5)) * k
        const dim = selectedFlow !== null && selectedFlow !== flow.id
        const active = selectedFlow === flow.id
        return (
          <g key={flow.id} role="button" tabIndex={0} className="cursor-pointer outline-none"
             aria-label={`${flow.from.name} vers ${flow.to.name}, ${flow.count}`}
             opacity={dim ? 0.25 : 1}
             onClick={() => onSelectFlow?.(flow.id)}
             onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectFlow?.(flow.id) } }}>
            <title>{`${flow.from.name} → ${flow.to.name} : ${flow.count}`}</title>
            <path d={d} fill="none" stroke="#FFFFFF" strokeWidth={width + 3 * k} strokeLinecap="round" />
            <path d={d} fill="none" stroke={style.color} strokeWidth={active ? width * 1.6 : width}
                  strokeDasharray={style.dash?.split(' ').map((v) => Number(v) * width).join(' ')}
                  strokeLinecap="round" markerEnd={`url(#fleche-${flow.confidence})`} />
            <path d={d} fill="none" stroke="transparent" strokeWidth={16 * k} />
          </g>
        )
      })}

      {/* noms des zones */}
      {colored.map((z) => (
        <text key={`t-${z.code}`} x={z.centroid[0]} y={z.centroid[1]} textAnchor="middle"
              dominantBaseline="middle" fontSize={(showRegions && !focus ? 10 : 15) * k} fontWeight={700}
              fill="#17231B" stroke="#FFFFFF" strokeWidth={3.5 * k} paintOrder="stroke" pointerEvents="none">
          {z.name.replace(' (district autonome)', '').replace('District autonome ', '')}
        </text>
      ))}

      {/* mes élevages */}
      {projected.mine.map(([x, y], i) => (
        <circle key={`m-${i}`} cx={x} cy={y} r={7 * k} fill="var(--focus)" stroke="#FFFFFF"
                strokeWidth={2.5 * k} pointerEvents="none" />
      ))}
    </svg>
  )
}
