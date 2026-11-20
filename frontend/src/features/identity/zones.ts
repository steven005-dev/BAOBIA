/** Zones pour les listes de choix (Ajouter un élevage, Inscrire un éleveur). */

import type { Zone } from './api'

/** Zones dans l'ordre de la hiérarchie, avec un retrait par niveau (lecture facile). */
export function zoneOptions(zones: Zone[]) {
  const children = new Map<string | null, Zone[]>()
  for (const zone of zones) {
    const list = children.get(zone.parent_id) ?? []
    list.push(zone)
    children.set(zone.parent_id, list)
  }
  const known = new Set(zones.map((z) => z.id))
  const roots = zones.filter((z) => !z.parent_id || !known.has(z.parent_id))
  const out: { value: string; label: string }[] = []
  const walk = (zone: Zone, depth: number) => {
    out.push({ value: zone.id, label: `${'  '.repeat(depth)}${zone.name}` })
    for (const child of children.get(zone.id) ?? []) walk(child, depth + 1)
  }
  roots.forEach((root) => walk(root, 0))
  return out
}

/** Les zones `rootIds` et toutes leurs zones filles (secteur d'un agent). */
export function zonesWithin(zones: Zone[], rootIds: string[]): Zone[] {
  const inside = new Set(rootIds)
  let grew = true
  while (grew) {
    grew = false
    for (const zone of zones) {
      if (zone.parent_id && inside.has(zone.parent_id) && !inside.has(zone.id)) {
        inside.add(zone.id)
        grew = true
      }
    }
  }
  return zones.filter((zone) => inside.has(zone.id))
}
