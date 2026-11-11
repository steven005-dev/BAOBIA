/**
 * Routes du module identity (responsable : chef de projet) : élevages, animaux, scan.
 * Remplacer les pages vides par les écrans du module ; ne pas modifier src/app/.
 */

import { PawPrint, ScanQrCode } from 'lucide-react'
import type { RouteObject } from 'react-router'

import { ModulePlaceholder } from '@/app/ModulePlaceholder'
import { mots } from '@/lib/vocabulaire'

export const identityRoutes: RouteObject[] = [
  { path: 'centres', element: <ModulePlaceholder title={mots.animaux} icon={PawPrint} /> },
  { path: 'scanner', element: <ModulePlaceholder title={mots.scanner} icon={ScanQrCode} /> },
]
