import { api } from '@/lib/api'

export interface DestinationShareCode {
  code: string
  expires_in_days: number
}

export interface ResolvedDestination {
  center_id: string
  center_name: string
}

export const movementApi = {
  shareDestinationCode: (centerId: string) =>
    api.post<DestinationShareCode>('/movements/destination-code/', { center_id: centerId }),
  resolveDestinationCode: (code: string) =>
    api.get<ResolvedDestination>(`/movements/destination-code/?code=${encodeURIComponent(code)}`),
}
