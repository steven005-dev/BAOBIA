/**
 * Messages (tous les profils) : les 50 derniers, les non lus en premier plan. Toucher un
 * message le marque lu et ouvre l'écran concerné (signalement, alerte, réception...).
 */

import { CheckCheck, ChevronRight, Inbox } from 'lucide-react'
import { useNavigate } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { Banner } from '@/components/Banner'
import { Button } from '@/components/Button'
import { EmptyState } from '@/components/EmptyState'
import { Loader } from '@/components/Loader'
import { useResource } from '@/features/identity/useResource'
import { cn } from '@/lib/utils'
import { messagesTextes } from '@/lib/vocabulaire'

import { notificationsApi, type AppNotification } from './api'
import { messageIcon, messageLink, messageText } from './text'

export function MessagesPage() {
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const professional = hasRole('veterinarian') || hasRole('authority')
  const list = useResource(notificationsApi.list, 'messages')

  if (list.loading && !list.data) return <Loader />
  if (list.error) return <Banner variant="error">{list.error.message}</Banner>
  const items = (list.data ?? []).filter((n) => messageText(n) !== null)
  const unread = items.filter((n) => !n.read_at)

  const open = async (n: AppNotification) => {
    if (!n.read_at) await notificationsApi.markRead([n.id]).catch(() => {})
    const link = messageLink(n, professional)
    if (link) navigate(link)
    else list.reload()
  }
  const readAll = async () => {
    await notificationsApi.markRead(unread.map((n) => n.id)).catch(() => {})
    list.reload()
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-title font-bold text-foreground">{messagesTextes.titre}</h1>
        {unread.length > 0 && (
          <Button variant="ghost" icon={CheckCheck} onClick={() => void readAll()}>
            {messagesTextes.toutLire}
          </Button>
        )}
      </div>
      {items.length === 0 ? (
        <EmptyState icon={Inbox} title={messagesTextes.aucun} />
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((n) => {
            const Icon = messageIcon(n)
            const isNew = !n.read_at
            return (
              <li key={n.id}>
                <button type="button" onClick={() => void open(n)}
                        className={cn('flex w-full items-start gap-3 rounded-lg border-2 bg-surface p-3 text-left shadow-card',
                          isNew ? 'border-primary' : 'border-border')}>
                  <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-md',
                    isNew ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground')}>
                    <Icon aria-hidden className="size-icon" />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-1">
                    <span className="flex flex-wrap items-center gap-2 text-caption text-muted-foreground">
                      {new Date(n.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}
                      {isNew && <span className="rounded-full bg-primary px-2 font-bold text-primary-foreground">{messagesTextes.nouveau}</span>}
                    </span>
                    <span className={cn('text-body', isNew && 'font-bold')}>{messageText(n)}</span>
                  </span>
                  {messageLink(n, professional) && <ChevronRight aria-hidden className="mt-2 size-icon shrink-0 text-muted-foreground" />}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
