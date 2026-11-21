/**
 * Tracés de Côte d'Ivoire projetés une seule fois (d3-geo, Mercator) pour la carte SVG.
 * Source : ci-zones.json (geoBoundaries CIV ADM1/ADM2, CC BY 4.0, simplifié).
 */

import { geoArea, geoMercator, geoPath, type GeoPermissibleObjects } from 'd3-geo'

import type { FlowConfidence } from '@/features/health/api'

import ciZones from './ci-zones.json'

interface ZoneShape {
  code: string
  name: string
  parent?: string
  geometry: GeoPermissibleObjects
}

export interface DrawnZone {
  code: string
  name: string
  parent?: string
  d: string
  centroid: [number, number]
  bounds: [[number, number], [number, number]]
}

export const WIDTH = 600
export const HEIGHT = 620
export const FULL: ViewBox = [0, 0, WIDTH, HEIGHT]
export type ViewBox = [number, number, number, number]

type Ring = [number, number][]

/** d3-geo lit le sens des contours (géométrie sphérique) : un contour « à l'envers » couvre
 * toute la Terre sauf la zone. Les données ouvertes suivent souvent la règle inverse (RFC 7946) :
 * on retourne chaque contour qui couvrirait plus d'une demi-sphère. */
function rewind(geometry: GeoPermissibleObjects): GeoPermissibleObjects {
  const multi = geometry as unknown as { type: string; coordinates: Ring[][] }
  const polygons = multi.coordinates.map((rings) =>
    rings.map((ring) =>
      geoArea({ type: 'Polygon', coordinates: [ring] } as GeoPermissibleObjects) > 2 * Math.PI
        ? [...ring].reverse() : ring,
    ),
  )
  return { type: 'MultiPolygon', coordinates: polygons } as GeoPermissibleObjects
}

/** Projection et tracés calculés une seule fois. */
function buildShapes() {
  const fix = (z: ZoneShape): ZoneShape => ({ ...z, geometry: rewind(z.geometry) })
  const districts = (ciZones.districts as unknown as ZoneShape[]).map(fix)
  const regions = (ciZones.regions as unknown as ZoneShape[]).map(fix)
  const projection = geoMercator().fitExtent(
    [[12, 12], [WIDTH - 12, HEIGHT - 12]],
    { type: 'FeatureCollection', features: districts.map((z) => ({ type: 'Feature', properties: {}, geometry: z.geometry })) } as GeoPermissibleObjects,
  )
  const path = geoPath(projection)
  const draw = (z: ZoneShape): DrawnZone => ({
    code: z.code, name: z.name, parent: z.parent,
    d: path(z.geometry) ?? '',
    centroid: path.centroid(z.geometry) as [number, number],
    bounds: path.bounds(z.geometry) as [[number, number], [number, number]],
  })
  return { projection, districts: districts.map(draw), regions: regions.map(draw) }
}

export const SHAPES = buildShapes()

export function boxFor(bounds: [[number, number], [number, number]]): ViewBox {
  const [[x0, y0], [x1, y1]] = bounds
  const pad = 0.12 * Math.max(x1 - x0, y1 - y0)
  let w = x1 - x0 + 2 * pad
  let h = y1 - y0 + 2 * pad
  // garder les proportions du cadre pour ne pas déformer
  if (w / h > WIDTH / HEIGHT) h = (w * HEIGHT) / WIDTH
  else w = (h * WIDTH) / HEIGHT
  const cx = (x0 + x1) / 2
  const cy = (y0 + y1) / 2
  return [cx - w / 2, cy - h / 2, w, h]
}

/** Style d'un flux selon sa confiance : trait plein, tirets ou pointillés (jamais la couleur seule). */
export const FLOW_STYLE: Record<FlowConfidence, { color: string; dash?: string }> = {
  confirmed: { color: '#175CD3' },
  one_side: { color: '#175CD3', dash: '7 5' },
  disputed: { color: '#9C2A56', dash: '1.5 4' },
}
