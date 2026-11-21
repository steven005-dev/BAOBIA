/**
 * Fiche de demande d'analyse de laboratoire (vétérinaire) : imprimée, elle accompagne les
 * prélèvements. Elle reprend le constat (signes, morts et malades, animaux et leurs
 * étiquettes), la maladie suspectée (pistes) et les prélèvements faits, avec un QR de
 * référence BAOBIA. Le suivi des résultats viendra après la démo (pas de changement de base ici).
 * Les réglages (maladie, prélèvements) ne sont pas imprimés (print:hidden).
 */

import { ArrowLeft, Printer } from 'lucide-react'
import QRCode from 'qrcode'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { Field } from '@/components/Field'
import { Loader } from '@/components/Loader'
import { Select } from '@/components/Select'
import { useResource } from '@/features/identity/useResource'
import { identityApi } from '@/features/identity/api'
import { formatShortCode } from '@/lib/shortCode'
import { APP_NAME, mots, pistesTextes } from '@/lib/vocabulaire'

import { healthApi } from './api'

function useQr(text: string) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    QRCode.toString(text, { type: 'svg', errorCorrectionLevel: 'M', margin: 1 }).then(
      (markup) => alive && setSrc(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`),
      () => alive && setSrc(null),
    )
    return () => {
      alive = false
    }
  }, [text])
  return src
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-2 border-b border-border py-1.5">
      <dt className="font-bold">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export function LabSheetPage() {
  const { reportId = '' } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const report = useResource(() => healthApi.report(reportId), reportId)
  const species = useResource(identityApi.species, 'especes')
  // undefined = pas encore choisi (première piste) ; '' = « À préciser »
  const [diseaseCode, setDiseaseCode] = useState<string | undefined>(undefined)
  const [counts, setCounts] = useState<Record<string, number>>({})
  const reference = `BAOBIA-${reportId.slice(0, 8).toUpperCase()}`
  const qr = useQr(`${reference} ${reportId}`)

  const leads = useMemo(() => report.data?.leads?.items ?? [], [report.data])
  const chosen = leads.find((l) => l.disease.code === (diseaseCode ?? leads[0]?.disease.code))

  if (report.loading) return <Loader />
  if (report.error) return <Banner variant="error">{report.error.message}</Banner>
  const r = report.data
  if (!r) return null
  const speciesLabel = (code: string) => species.data?.find((s) => s.code === code)?.label_fr ?? code
  const samples = chosen?.samples ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 print:hidden">
        <Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)} className="self-start">
          {mots.retour}
        </Button>
        <h1 className="text-title font-bold text-foreground">{pistesTextes.ficheLabo}</h1>
        <Card>
          <Field label={pistesTextes.maladieSuspectee}>
            <Select value={chosen?.disease.code ?? ''} onChange={(e) => setDiseaseCode(e.target.value)}
                    options={[
                      ...leads.map((l) => ({ value: l.disease.code, label: `${l.disease.label_fr} (${l.strength_label})` })),
                      { value: '', label: pistesTextes.aPreciser },
                    ]} />
          </Field>
          {samples.length > 0 && (
            <fieldset className="mt-3 flex flex-col gap-2">
              <legend className="font-bold">{pistesTextes.prelevementsFaits} ({pistesTextes.nombre})</legend>
              {samples.map((s) => (
                <label key={s.nature} className="flex items-center gap-3 text-body">
                  <input type="number" min={0} max={50} inputMode="numeric"
                         className="h-touch w-20 rounded-md border-2 border-border px-2"
                         value={counts[s.nature] ?? 0}
                         onChange={(e) => setCounts((c) => ({ ...c, [s.nature]: Number(e.target.value) || 0 }))} />
                  {s.nature}
                </label>
              ))}
            </fieldset>
          )}
          <Button icon={Printer} onClick={() => window.print()} className="mt-4">
            {pistesTextes.imprimer}
          </Button>
        </Card>
      </div>

      {/* La fiche elle-même : seule partie imprimée. */}
      <article className="print-sheet flex flex-col gap-4 rounded-lg border-2 border-foreground bg-card p-5 text-small text-foreground">
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="font-bold">{APP_NAME}</p>
            <h2 className="text-subtitle font-bold">{pistesTextes.titreLabo}</h2>
            <p>{pistesTextes.reference} : <b>{reference}</b> · {new Date().toLocaleDateString('fr-FR')}</p>
          </div>
          {qr && <img src={qr} alt={reference} className="size-24 shrink-0" />}
        </header>

        <dl>
          <Row label={pistesTextes.demandeur}>{user?.full_name}</Row>
          <Row label={pistesTextes.elevage}>{r.center.name}</Row>
          <Row label={pistesTextes.zone}>{r.center.zone_name ?? '—'}</Row>
          <Row label={pistesTextes.dateObservation}>{new Date(r.occurred_at).toLocaleString('fr-FR')}</Row>
          <Row label={pistesTextes.mortsMalades}>{r.dead_count} / {r.affected_count - r.dead_count}</Row>
          <Row label={pistesTextes.signes}>{r.symptoms.map((s) => s.label_fr).join(', ') || '—'}</Row>
          <Row label={pistesTextes.maladieSuspectee}>
            {chosen ? `${chosen.disease.label_fr} (${chosen.strength_label})` : pistesTextes.aPreciser}
          </Row>
        </dl>

        <section>
          <h3 className="font-bold">{pistesTextes.animauxPreleves}</h3>
          <table className="mt-1 w-full border-collapse text-left">
            <thead>
              <tr className="border-b-2 border-foreground">
                <th className="py-1">{pistesTextes.etiquette}</th><th>{pistesTextes.espece}</th><th>{pistesTextes.etat}</th>
              </tr>
            </thead>
            <tbody>
              {r.subjects.map((s) => (
                <tr key={s.unit_id} className="border-b border-border">
                  <td className="py-1 font-mono">{s.code ? formatShortCode(s.code) : '—'}{s.local_name ? ` (${s.local_name})` : ''}</td>
                  <td>{speciesLabel(s.species_code)}</td>
                  <td>{s.condition === 'dead' ? pistesTextes.mort : pistesTextes.malade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h3 className="font-bold">{pistesTextes.prelevementsFaits}</h3>
          <ul className="mt-1 list-disc pl-5">
            {samples.map((s) => (
              <li key={s.nature}><b>{counts[s.nature] ?? 0} ×</b> {s.nature} ({s.conditioning})</li>
            ))}
          </ul>
          {chosen?.zoonosis && <p className="mt-1 font-bold">{pistesTextes.zoonose}</p>}
          {r.leads && <p className="mt-1 text-caption">{r.leads.lab_note}</p>}
        </section>

        <footer className="grid grid-cols-2 gap-4 pt-2">
          <div className="min-h-20 rounded-md border border-border p-2">{pistesTextes.signature}</div>
          <div className="min-h-20 rounded-md border border-border p-2">{pistesTextes.receptionLabo}</div>
        </footer>
        <p className="text-caption">{pistesTextes.donneesSimulees}</p>
      </article>
    </div>
  )
}
