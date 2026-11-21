/**
 * Pistes de maladie d'un signalement (vétérinaire, autorité) : pour chaque maladie possible,
 * la force de la piste et POURQUOI (règles de apps/health/leads.py). Jamais un diagnostic :
 * le vétérinaire examine et décide. Les fiches restent à valider (bandeau).
 */

import { FlaskConical, Stethoscope } from 'lucide-react'

import { Banner } from '@/components/Banner'
import { Card } from '@/components/Card'
import { cn } from '@/lib/utils'
import { pistesTextes } from '@/lib/vocabulaire'

import type { DiseaseLead, Leads } from './api'

/** Force de la piste : couleurs neutres (jamais celles des états sanitaires), toujours avec le mot. */
const STRENGTH_CLASSES: Record<DiseaseLead['strength'], string> = {
  strong: 'border-info bg-info-bg text-info',
  medium: 'border-primary bg-accent text-primary',
  weak: 'border-border bg-muted text-muted-foreground',
}

function LeadItem({ lead }: { lead: DiseaseLead }) {
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-card-title font-bold">{lead.disease.label_fr}</span>
        <span className={cn('rounded-full border-2 px-2 py-0.5 text-small font-bold', STRENGTH_CLASSES[lead.strength])}>
          {lead.strength_label}
        </span>
        {lead.major_total > 0 && (
          <span className="text-small text-muted-foreground">
            {lead.major_found}/{lead.major_total} {pistesTextes.signesMajeurs}
          </span>
        )}
        {lead.disease.is_notifiable && (
          <span className="rounded-full bg-warning-bg px-2 py-0.5 text-small font-bold text-warning">
            {pistesTextes.declarationObligatoire}
          </span>
        )}
      </div>
      <ul className="list-disc pl-5 text-small">
        {lead.explanation.map((line) => <li key={line}>{line}</li>)}
      </ul>
      <p className="text-small text-muted-foreground">
        {pistesTextes.contagion} {lead.spread} · {pistesTextes.incubation} {lead.incubation_days[0]} à{' '}
        {lead.incubation_days[1]} {pistesTextes.jours}
      </p>
      {(lead.caution || lead.zoonosis) && (
        <Banner variant="warning">{lead.caution ?? pistesTextes.zoonose}</Banner>
      )}
      <details className="text-small">
        <summary className="flex cursor-pointer items-center gap-1 font-bold text-primary">
          <FlaskConical aria-hidden className="size-icon-small" /> {pistesTextes.prelevements}
        </summary>
        <ul className="mt-1 list-disc pl-5">
          {lead.samples.map((s) => <li key={s.nature}><b>{s.nature}</b> : {s.conditioning}</li>)}
        </ul>
      </details>
    </li>
  )
}

export function DiseaseLeads({ leads }: { leads: Leads }) {
  return (
    <Card title={pistesTextes.titre} icon={Stethoscope}>
      <p className="text-small text-muted-foreground">{leads.warning}</p>
      <p className="text-small"><b>{pistesTextes.alerteGenerale}</b> {leads.general_alert}</p>
      {!leads.validated && <Banner variant="info">{pistesTextes.fichesAValider}</Banner>}
      {leads.items.length === 0 ? (
        <p className="text-body">{pistesTextes.aucune}</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-3">
          {leads.items.map((lead) => <LeadItem key={lead.disease.code} lead={lead} />)}
        </ul>
      )}
    </Card>
  )
}
