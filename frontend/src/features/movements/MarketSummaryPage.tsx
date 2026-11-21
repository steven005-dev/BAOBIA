/**
 * Bilan du jour d'un marché (guide de réalisation des ajouts, 5) : chiffres agrégés pour le
 * gestionnaire du marché et l'Autorité. Aucun nom d'élevage ; une zone d'origine de moins
 * de 5 animaux est regroupée dans « Autres zones » (calculé par le serveur).
 */

import { useState } from 'react'
import { ArrowLeft, BarChart3 } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router'

import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'

import { identityApi } from '@/features/identity/api'
import { useResource } from '@/features/identity/useResource'

import { tracingApi } from './api'

function today() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
}

function Figure({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border-2 border-border bg-surface p-4">
      <span className="text-number font-bold text-foreground">{value}</span>
      <span className="text-small text-muted-foreground">{label}</span>
    </div>
  )
}

export function MarketSummaryPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const centersResource = useResource(identityApi.centers, 'centres-bilan')
  const markets = (centersResource.data ?? []).filter((center) => center.center_type === 'market')
  const [marketId, setMarketId] = useState(params.get('marche') ?? '')
  const market = markets.find((item) => item.id === marketId) ?? markets[0]
  const [day, setDay] = useState(today())
  const summary = useResource(
    () => tracingApi.summary(market!.id, day),
    market ? `bilan-${market.id}-${day}` : null,
  )

  if (centersResource.loading) return <Loader />
  if (!market) {
    return <EmptyState icon={BarChart3} title="Aucun marché" text="Le bilan est réservé au marché et à l’Autorité." />
  }
  const data = summary.data

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-title font-bold text-foreground">Bilan du jour</h1>
      {markets.length > 1 && (
        <Field label="Marché">
          <Select value={market.id} onChange={(event) => setMarketId(event.target.value)}
                  options={markets.map((item) => ({ value: item.id, label: item.name }))} />
        </Field>
      )}
      <Field label="Jour">
        <Input type="date" value={day} max={today()} onChange={(event) => setDay(event.target.value || today())} />
      </Field>
      {summary.loading && <Loader />}
      {summary.error && <Banner variant="error">{summary.error.message}</Banner>}
      {data && (
        <>
          <p className="text-body font-bold text-foreground">{data.market}</p>
          <div className="grid grid-cols-2 gap-3">
            <Figure label="Entrés" value={data.entered} />
            <Figure label="Sortis" value={data.left} />
            <Figure label="Inconnus" value={data.unknown} />
            <Figure label="Alertes" value={data.warnings} />
          </div>
          <section aria-labelledby="species-heading" className="flex flex-col gap-2">
            <h2 id="species-heading" className="text-subtitle font-bold text-foreground">Par espèce</h2>
            {data.by_species.length === 0 ? (
              <p className="text-body text-muted-foreground">Aucun animal ce jour.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {data.by_species.map((row) => (
                  <li key={`${row.species}-${row.direction}`} className="text-body text-foreground">
                    {row.species} · {row.direction === 'in' ? 'entrés' : 'sortis'} : <strong>{row.count}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section aria-labelledby="zones-heading" className="flex flex-col gap-2">
            <h2 id="zones-heading" className="text-subtitle font-bold text-foreground">Zones d’origine (entrées)</h2>
            {data.by_origin_zone.length === 0 ? (
              <p className="text-body text-muted-foreground">Aucune entrée ce jour.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {data.by_origin_zone.map((row) => (
                  <li key={row.zone} className="text-body text-foreground">{row.zone} : <strong>{row.count}</strong></li>
                ))}
              </ul>
            )}
            <p className="text-small text-muted-foreground">
              Moins de 5 animaux d’une même zone : regroupés dans « Autres zones », pour ne désigner aucun élevage.
            </p>
          </section>
        </>
      )}
      <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate('/mouvements/marche')}>Retour au marché</Button>
    </section>
  )
}
