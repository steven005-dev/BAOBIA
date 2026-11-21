/**
 * Routes du module mouvements (responsable : Konan Romuald).
 * Ajouter ici les écrans (Transférer, Recevoir, Confirmer...) ; ne pas modifier src/app/.
 * Exemple : { path: 'mouvements/recevoir', element: <ReceptionPage /> }
 */

import type { RouteObject } from 'react-router'

import { DeclareMovementForm } from './DeclareMovementForm'
import { ConfirmMovementReceiptPage } from './ConfirmMovementReceiptPage'
import { MarketPage } from './MarketPage'
import { MarketSummaryPage } from './MarketSummaryPage'
import { MovementHistoryPage } from './MovementHistoryPage'
import { ShareDestinationCodePage } from './ShareDestinationCodePage'
import { installMovementQueue } from '@/features/offline/queue'

installMovementQueue()

export const movementsRoutes: RouteObject[] = [
  { path: 'mouvements', element: <DeclareMovementForm /> },
  { path: 'mouvements/recevoir', element: <ConfirmMovementReceiptPage /> },
  { path: 'mouvements/partager', element: <ShareDestinationCodePage /> },
  { path: 'mouvements/historique', element: <MovementHistoryPage /> },
  { path: 'mouvements/marche', element: <MarketPage /> },
  { path: 'mouvements/marche/bilan', element: <MarketSummaryPage /> },
]
