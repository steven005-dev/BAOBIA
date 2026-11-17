/**
 * Ajouter un élevage (éleveur, commerçant) : nom, zone, espèces élevées.
 * L'utilisateur devient le détenteur. Identifiant créé sur le téléphone (envoi rejouable).
 */

import { ArrowLeft, CirclePlus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { useToast } from '@/components/Toast'
import { ApiError } from '@/lib/api'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

import { identityApi, newUuid, type Zone } from './api'
import { speciesIcon } from './speciesIcon'
import { useResource } from './useResource'

/** Zones dans l'ordre de la hiérarchie, avec un retrait par niveau (lecture facile). */
function zoneOptions(zones: Zone[]) {
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
    out.push({ value: zone.id, label: `${'  '.repeat(depth)}${zone.name}` })
    for (const child of children.get(zone.id) ?? []) walk(child, depth + 1)
  }
  roots.forEach((root) => walk(root, 0))
  return out
}

export function AddCenterPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const zones = useResource(identityApi.zones, 'zones')
  const species = useResource(identityApi.species, 'especes')

  const [centerId] = useState(newUuid)
  const [name, setName] = useState('')
  const [zoneId, setZoneId] = useState('')
  const [speciesIds, setSpeciesIds] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (zones.loading || species.loading) return <Loader />
  const loadError = zones.error ?? species.error
  if (loadError) return <Banner variant="error">{loadError.message}</Banner>

  const send = async () => {
    if (!name.trim() || !zoneId || speciesIds.length === 0) {
      setError(messages.champManquant)
      return
    }
    setSending(true)
    setError(null)
    try {
      await identityApi.addCenter(centerId, { name: name.trim(), zone_id: zoneId, species_ids: speciesIds })
      toast.show(messages.elevageAjoute, 'success')
      navigate(`/centres?elevage=${centerId}`, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : erreurs.serveur)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{titres.ajouterElevage}</h1>

      <Field label={champs.nomElevage}>
        <Input value={name} maxLength={160} onChange={(e) => setName(e.target.value)} />
      </Field>

      <Field label={champs.zone}>
        <Select
          value={zoneId}
          onChange={(e) => setZoneId(e.target.value)}
          placeholder={champs.choisir}
          options={zoneOptions(zones.data ?? [])}
        />
      </Field>

      <ChoiceGrid
        multiple
        label={champs.especesElevees}
        value={speciesIds}
        onChange={setSpeciesIds}
        options={(species.data ?? []).map((s) => ({ value: s.id, label: s.label_fr, icon: speciesIcon(s.code) }))}
      />

      {error && <Banner variant="error">{error}</Banner>}

      <div className="flex flex-col gap-3">
        <Button icon={CirclePlus} onClick={() => void send()} loading={sending}>
          {mots.ajouter}
        </Button>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)} disabled={sending}>
          {mots.retour}
        </Button>
      </div>
    </div>
  )
}
