import { Banner } from '@/components/Banner'
import type { OperationStatus } from '@/offline'

export function SyncStatusBanner({ status }: { status: OperationStatus }) {
  if (status === 'sent') {
    return <Banner variant="success">Envoyé au serveur.</Banner>
  }
  if (status === 'check') {
    return <Banner variant="error">À vérifier avant de continuer.</Banner>
  }
  return <Banner variant="info">En attente d’envoi.</Banner>
}
