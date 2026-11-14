/**
 * Messages non lus, en cartes (Accueil de l'éleveur, page Alertes...). Chaque carte a
 * une icône, un texte neutre du vocabulaire et le bouton Fermer (marque le message lu).
 * N'affiche rien s'il n'y a aucun message ou si le réseau est coupé.
 *
 * Exemple : <UnreadMessages />
 */

import { Clock, Siren, Stethoscope, TriangleAlert, X, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/Button'
import { Card } from '@/components/Card'
import { messages, mots, textesNotifications } from '@/lib/vocabulaire'

import { notificationsApi, type AppNotification, type NotificationKind } from './api'

const ICONS: Record<NotificationKind, LucideIcon> = {
  exposure: TriangleAlert,
  alert: Siren,
  zone_cluster_review: Stethoscope,
  escalation: Clock,
}

export function UnreadMessages() {
  const [items, setItems] = useState<AppNotification[]>([])

  useEffect(() => {
    let alive = true
    notificationsApi.list().then(
      (list) => alive && setItems(list.filter((n) => !n.read_at && textesNotifications[n.message_code])),
      () => {}, // hors ligne ou erreur : pas de message, l'Accueil reste utilisable
    )
    return () => {
      alive = false
    }
  }, [])

  if (items.length === 0) return null

  const close = (id: string) => {
    setItems((current) => current.filter((n) => n.id !== id))
    notificationsApi.markRead([id]).catch(() => {})
  }

  return (
    <section className="flex flex-col gap-3" aria-label={messages.nouveauxMessages}>
      <h2 className="text-subtitle font-bold text-foreground">{messages.nouveauxMessages}</h2>
      {items.map((n) => (
        <Card
          key={n.id}
          icon={ICONS[n.kind] ?? TriangleAlert}
          title={new Date(n.created_at).toLocaleDateString('fr-CI')}
          footer={
            <Button variant="ghost" icon={X} onClick={() => close(n.id)}>
              {mots.fermer}
            </Button>
          }
        >
          <p className="text-body text-foreground">{textesNotifications[n.message_code]}</p>
        </Card>
      ))}
    </section>
  )
}
