import { useQuery } from '@tanstack/react-query'

import { api, type Me } from '@/shared/api/client'

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me'), staleTime: 5 * 60_000 })
}
