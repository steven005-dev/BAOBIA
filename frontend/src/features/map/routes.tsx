/**
 * Routes du module carte (responsable : Yéo). La légende et les zones réutilisent
 * HEALTH_STATES (src/lib/healthStates.ts).
 * La carte est chargée à part (tracés + d3-geo) : elle ne ralentit pas les autres écrans.
 * Le fichier est quand même mis en cache par la PWA (precache-manifest) : elle marche hors ligne.
 * Ajouter ici les écrans ; ne pas modifier src/app/.
 */

import type { RouteObject } from 'react-router'

export const mapRoutes: RouteObject[] = [
  { path: 'carte', lazy: async () => ({ Component: (await import('./MapPage')).MapPage }) },
]
