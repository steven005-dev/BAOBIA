/**
 * Messages reçus (backend : apps/notifications). Le serveur envoie un code de message ;
 * le texte vient du vocabulaire (textesNotifications).
 */

import { api } from '@/lib/api'

export type NotificationKind = 'exposure' | 'alert' | 'zone_cluster_review' | 'escalation'

export interface AppNotification {
  id: string
  kind: NotificationKind
  message_code: string
  params: Record<string, string | number | boolean>
  alert_id: string | null
  status: 'pending' | 'sent' | 'read' | 'failed'
  created_at: string
  read_at: string | null
}

export const notificationsApi = {
  list: () => api.get<AppNotification[]>('/notifications/'),
  unreadCount: () => api.get<{ unread: number }>('/notifications/unread-count/'),
  /** Marquer lu n'est pas une action terrain critique : envoi direct, sans file hors ligne. */
  markRead: (ids: string[]) => api.post<{ marked: number }>('/notifications/read/', { ids }),
}
