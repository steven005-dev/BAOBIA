/** Routes du module notifications (chef de projet) : centre de messages de tous les profils. */

import type { RouteObject } from 'react-router'

import { MessagesPage } from './MessagesPage'

export const notificationsRoutes: RouteObject[] = [{ path: 'messages', element: <MessagesPage /> }]
