/**
 * Page /composants : tous les composants du socle dans tous leurs états.
 * DÉVELOPPEMENT SEULEMENT (route ajoutée si import.meta.env.DEV, absente du build).
 * Les textes d'exemple ci-dessous sont des données de démonstration.
 */

import {
  ArrowLeftRight,
  CircleCheck,
  CirclePlus,
  Flag,
  HeartPulse,
  PackageCheck,
  PawPrint,
  Thermometer,
  Trash2,
  Users,
  Warehouse,
  Wind,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { fieldNavigation, deskNavigation } from '@/app/navigation'
import { AlertLevelBadge } from '@/components/AlertLevelBadge'
import { AnimalCard } from '@/components/AnimalCard'
import { AppHeader } from '@/components/AppHeader'
import { Banner } from '@/components/Banner'
import { BigChoiceTile } from '@/components/BigChoiceTile'
import { BottomNav } from '@/components/BottomNav'
import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { ChoiceGrid } from '@/components/ChoiceGrid'
import { CodeInput } from '@/components/CodeInput'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { DemoDataNotice } from '@/components/DemoDataNotice'
import { EmptyState } from '@/components/EmptyState'
import { Field } from '@/components/Field'
import { Input } from '@/components/Input'
import { Loader } from '@/components/Loader'
import { NumberStepper } from '@/components/NumberStepper'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { PhoneInput } from '@/components/PhoneInput'
import { Select } from '@/components/Select'
import { SidebarNav } from '@/components/SidebarNav'
import { Skeleton } from '@/components/Skeleton'
import { StatusBadge } from '@/components/StatusBadge'
import { useToast } from '@/components/Toast'
import { HEALTH_STATE_ORDER } from '@/lib/healthStates'
import { isValidShortCode, SHORT_CODE_LENGTH } from '@/lib/shortCode'
import { champs, erreurs, messages, mots, titres } from '@/lib/vocabulaire'

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="flex flex-col gap-4 border-t border-border pt-6">
      <h2 className="text-subtitle font-bold text-foreground">{title}</h2>
      {children}
    </section>
  )
}

function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-3">{children}</div>
}

const ESPECES = [
  { value: 'cattle', label: 'Bovin', icon: PawPrint },
  { value: 'goat', label: 'Chèvre', icon: PawPrint },
  { value: 'poultry', label: 'Volaille', icon: Users },
]
const SYMPTOMES = [
  { value: 'fever', label: 'Fièvre', icon: Thermometer },
  { value: 'cough', label: 'Toux', icon: Wind },
  { value: 'weak', label: 'Faiblesse', icon: HeartPulse },
]

export default function ComponentsPage() {
  const toast = useToast()
  const [phone, setPhone] = useState('07070707')
  const [code, setCode] = useState('23456789')
  const [badCode, setBadCode] = useState('23456789A')
  const [espece, setEspece] = useState<string | null>('cattle')
  const [symptomes, setSymptomes] = useState<string[]>(['fever'])
  const [quantite, setQuantite] = useState(10)
  const [select, setSelect] = useState('')
  const [dialog, setDialog] = useState<'none' | 'primary' | 'danger'>('none')
  const [selectedTile, setSelectedTile] = useState(true)

  const codeError = (value: string) =>
    value.length < SHORT_CODE_LENGTH ? erreurs.codeIncomplet : isValidShortCode(value) ? null : erreurs.codeIncorrect

  return (
    <div className="min-h-dvh bg-background pb-12">
      <AppHeader title={titres.composants} onListen={() => toast.show(mots.ecouter, 'info')} />
      <DemoDataNotice />
      <main className="mx-auto flex max-w-mobile flex-col gap-8 px-4 py-6 lg:max-w-form">
        <Section id="boutons" title="Button">
          <Button icon={CircleCheck} fullWidth>{mots.confirmer}</Button>
          <Button icon={CircleCheck} fullWidth disabled>{mots.confirmer}</Button>
          <Button icon={CircleCheck} fullWidth loading>{mots.envoyer}</Button>
          <Row>
            <Button variant="secondary" icon={ArrowLeftRight}>{mots.transferer}</Button>
            <Button variant="secondary" icon={ArrowLeftRight} disabled>{mots.transferer}</Button>
          </Row>
          <Row>
            <Button variant="danger" icon={Trash2}>{mots.supprimer}</Button>
            <Button variant="danger" icon={Trash2} disabled>{mots.supprimer}</Button>
            <Button variant="ghost" icon={PackageCheck}>{mots.recevoir}</Button>
          </Row>
        </Section>

        <Section id="champs" title="Field, Input, PhoneInput, CodeInput, Select">
          <Field label={mots.rechercher} help="Aide : nom ou code">
            <Input type="search" placeholder={mots.rechercher} />
          </Field>
          <Field label={mots.rechercher} error={erreurs.saisie}>
            <Input defaultValue="Valeur refusée" />
          </Field>
          <Field label={mots.rechercher}>
            <Input disabled defaultValue="Désactivé" />
          </Field>
          <Field label={champs.telephone} help={champs.telephoneAide} error={phone.length < 10 ? erreurs.telephoneIncomplet : null}>
            <PhoneInput value={phone} onValueChange={setPhone} />
          </Field>
          <Field label={champs.codeEtiquette} help={champs.codeEtiquetteAide} error={codeError(code)}>
            <CodeInput value={code} onValueChange={setCode} />
          </Field>
          <Field label={`${champs.codeEtiquette} (contrôle faux)`} error={codeError(badCode)}>
            <CodeInput value={badCode} onValueChange={setBadCode} />
          </Field>
          <Field label={`${champs.codeEtiquette} (valide)`} error={codeError('23456789N')}>
            <CodeInput value="23456789N" onValueChange={() => {}} readOnly />
          </Field>
          <Field label={champs.espece}>
            <Select value={select} onChange={(e) => setSelect(e.target.value)} placeholder={champs.choisir}
              options={ESPECES.map(({ value, label }) => ({ value, label }))} />
          </Field>
        </Section>

        <Section id="choix" title="ChoiceGrid, BigChoiceTile, NumberStepper">
          <ChoiceGrid label={`${champs.espece} (un choix)`} value={espece} onChange={setEspece} options={ESPECES} />
          <ChoiceGrid multiple label={`${mots.symptomes} (plusieurs)`} value={symptomes} onChange={setSymptomes} options={SYMPTOMES} />
          <div className="grid grid-cols-2 gap-3">
            <BigChoiceTile icon={CirclePlus} label={mots.ajouter} onClick={() => toast.show(messages.animalAjoute, 'success')} />
            <BigChoiceTile icon={Flag} label={mots.signaler} role="checkbox" selected={selectedTile} onClick={() => setSelectedTile((s) => !s)} />
            <BigChoiceTile icon={ArrowLeftRight} label={mots.transferer} description="Désactivé" disabled />
            <BigChoiceTile icon={PackageCheck} label={mots.recevoir} to="/composants" />
          </div>
          <NumberStepper label={champs.quantite} value={quantite} onChange={setQuantite} min={1} max={50} />
        </Section>

        <Section id="etats" title="StatusBadge, AlertLevelBadge">
          <Row>{HEALTH_STATE_ORDER.map((state) => <StatusBadge key={state} state={state} />)}</Row>
          <Row>{HEALTH_STATE_ORDER.map((state) => <StatusBadge key={state} state={state} size="large" />)}</Row>
          <Row>
            <AlertLevelBadge level={1} />
            <AlertLevelBadge level={2} />
            <AlertLevelBadge level={3} />
          </Row>
        </Section>

        <Section id="messages" title="Banner, Toast">
          <Banner variant="success">{messages.transfertEnvoye}</Banner>
          <Banner variant="error">{erreurs.reseau}</Banner>
          <Banner variant="info" title={mots.information}>{messages.signalementEnvoye}</Banner>
          <Banner variant="warning" title={mots.aVerifier}>{messages.aVerifier}</Banner>
          <Row>
            <Button variant="secondary" icon={CircleCheck} onClick={() => toast.show(messages.receptionEnregistree, 'success')}>Toast succès</Button>
            <Button variant="secondary" icon={Flag} onClick={() => toast.show(erreurs.serveur, 'error')}>Toast erreur</Button>
            <Button variant="secondary" icon={Flag} onClick={() => toast.show(messages.enAttente, 'warning')}>Toast attente</Button>
          </Row>
        </Section>

        <Section id="reseau" title="OfflineIndicator, DemoDataNotice">
          <div className="flex flex-wrap gap-3 rounded-md bg-primary p-3">
            <OfflineIndicator online pending={0} />
            <OfflineIndicator online pending={3} />
            <OfflineIndicator online={false} pending={0} />
            <OfflineIndicator online={false} pending={2} />
          </div>
          <OfflineIndicator variant="banner" online={false} pending={2} />
          <OfflineIndicator variant="banner" online pending={1} />
          <DemoDataNotice />
        </Section>

        <Section id="cartes" title="Card, AnimalCard">
          <Card title="Élevage A (simulé)" icon={Warehouse} aside={<StatusBadge state="watch" />}
            footer={<Button variant="secondary" icon={ArrowLeftRight} fullWidth>{mots.transferer}</Button>}>
            12 animaux, 2 lots
          </Card>
          <AnimalCard shortCode="23456789N" name="Animal 1 (simulé)" species="Bovin" state="normal" to="/composants" />
          <AnimalCard shortCode="Z9Y8X7W6Q" name="Lot 1 (simulé)" species="Volaille" kind="lot" size={40} state="exposure" />
          <AnimalCard species="Chèvre" state="unknown" />
        </Section>

        <Section id="vides" title="EmptyState, Loader, Skeleton">
          <EmptyState icon={PawPrint} title="Aucun animal" text={messages.pageVide}
            action={<Button icon={CirclePlus}>{mots.ajouter}</Button>} />
          <Loader />
          <Skeleton className="h-touch-primary w-full" />
          <Skeleton className="h-28 w-full" />
        </Section>

        <Section id="fenetres" title="ConfirmDialog">
          <Row>
            <Button variant="secondary" icon={CircleCheck} onClick={() => setDialog('primary')}>Ouvrir : confirmer</Button>
            <Button variant="secondary" icon={Trash2} onClick={() => setDialog('danger')}>Ouvrir : supprimer</Button>
          </Row>
          <ConfirmDialog open={dialog === 'primary'} title="Confirmer la réception ?"
            onConfirm={() => { setDialog('none'); toast.show(messages.transfertConfirme, 'success') }}
            onCancel={() => setDialog('none')}>
            3 animaux venant de l'Élevage A (simulé).
          </ConfirmDialog>
          <ConfirmDialog open={dialog === 'danger'} title="Supprimer cette photo ?" variant="danger"
            confirmLabel={mots.supprimer} confirmIcon={Trash2}
            onConfirm={() => setDialog('none')} onCancel={() => setDialog('none')} />
        </Section>

        <Section id="navigation" title="AppHeader, BottomNav, SidebarNav">
          <AppHeader className="static" />
          <AppHeader className="static" title="Élevage A (simulé)" onBack={() => {}} onListen={() => {}} />
          <BottomNav items={fieldNavigation} className="static" />
          <BottomNav items={deskNavigation} className="static" />
          <SidebarNav items={deskNavigation} className="rounded-md border" />
        </Section>
      </main>
    </div>
  )
}
