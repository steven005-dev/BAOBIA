/**
 * Animaux (gabarit Liste) : les animaux et lots présents dans un de mes élevages.
 * Action principale : Ajouter. Plusieurs élevages : un choix en haut (?elevage=<id>).
 */

import { CirclePlus, PawPrint, Warehouse } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router'

import { AnimalCard } from '@/components/AnimalCard'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { messages, mots } from '@/lib/vocabulaire'

import { identityApi } from './api'
import { useResource } from './useResource'

export function AnimalsPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const centers = useResource(identityApi.centers, 'centres')

  const list = centers.data ?? []
  const chosen = params.get('elevage')
  const center = list.find((c) => c.id === chosen) ?? list[0]
  const units = useResource(
    () => identityApi.centerUnits(center?.id ?? ''),
    center ? center.id : null,
  )

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{mots.animaux}</h1>

      {centers.loading && <Loader />}
      {centers.error && <Banner variant="error">{centers.error.message}</Banner>}
      {centers.data && list.length === 0 && (
        <EmptyState icon={Warehouse} title={messages.aucunElevage} text={messages.aucunElevageAide} />
      )}

      {center && (
        <>
          {list.length > 1 && (
            <Field label={mots.elevage}>
              <Select
                value={center.id}
                onChange={(e) => setParams({ elevage: e.target.value }, { replace: true })}
                options={list.map((c) => ({ value: c.id, label: c.name }))}
              />
            </Field>
          )}
          {list.length === 1 && <p className="text-body text-muted-foreground">{center.name}</p>}

          <Button icon={CirclePlus} onClick={() => navigate(`/centres/${center.id}/ajouter`)}>
            {mots.ajouter}
          </Button>

          {units.loading && <Loader />}
          {units.error && <Banner variant="error">{units.error.message}</Banner>}
          {units.data && units.data.length === 0 && (
            <EmptyState icon={PawPrint} title={messages.aucunAnimal} text={messages.aucunAnimalAide} />
          )}
          {units.data && units.data.length > 0 && (
            <ul className="flex flex-col gap-3">
              {units.data.map((unit) => (
                <li key={unit.id}>
                  <AnimalCard
                    shortCode={unit.label_code}
                    name={unit.local_name}
                    species={unit.species.label_fr}
                    kind={unit.kind}
                    size={unit.size}
                    to={`/centres/animaux/${unit.id}`}
                  />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
