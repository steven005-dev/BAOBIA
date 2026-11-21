/**
 * Cloche de l'en-tête (tous les profils) : nombre de messages non lus, mène à « Messages ».
 * Le nombre est relu à l'ouverture, toutes les 60 s et quand on revient sur l'onglet ;
 * sans réseau, la cloche reste affichée sans nombre.
 */

import { Bell } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'

import { messagesTextes } from '@/lib/vocabulaire'

import { notificationsApi } from './api'

export function NotificationBell() {
  const [unread, setUnread] = useState(0)
  const location = useLocation()

  useEffect(() => {
    let alive = true
    const load = () => notificationsApi.unreadCount().then(
      (r) => alive && setUnread(r.unread),
      () => {},
    )
    void load()
    const timer = window.setInterval(load, 60_000)
    window.addEventListener('focus', load)
    return () => {
      alive = false
      window.clearInterval(timer)
      window.removeEventListener('focus', load)
    }
  }, [location.pathname])

  return (
    <Link to="/messages" aria-label={unread ? messagesTextes.nonLus(unread) : messagesTextes.ouvrir}
          className="relative flex h-touch shrink-0 items-center gap-1.5 rounded-full px-2 text-caption font-bold text-primary-foreground hover:bg-primary-hover sm:px-3">
      {/* La pastille est posée sur la cloche, jamais sur le mot. */}
      <span className="relative flex">
        <Bell aria-hidden className="size-icon" />
        {unread > 0 && (
          <span className="absolute -top-2 -right-2.5 flex min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-caption font-bold leading-5 text-destructive-foreground ring-2 ring-primary">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </span>
      <span className="hidden sm:inline">{messagesTextes.ouvrir}</span>
    </Link>
  )
}
