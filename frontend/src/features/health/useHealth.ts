import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type Health = { status: string; database: string; pgvector: string | null }

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api<Health>('/health'),
  })
}
