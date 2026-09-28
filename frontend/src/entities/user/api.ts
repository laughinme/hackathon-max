import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type Building, type House, type Me } from '@/shared/api/client'

export const userKeys = {
  me: ['me'] as const,
  house: ['me', 'house'] as const,
  demoBuildings: ['buildings', 'demo'] as const,
}

export function useMe() {
  return useQuery({ queryKey: userKeys.me, queryFn: () => api<Me>('/me'), staleTime: 5 * 60_000 })
}

/** The resident's building with its pulse and the signed leaflet link. */
export function useHouse(enabled = true) {
  return useQuery({ queryKey: userKeys.house, queryFn: () => api<House>('/me/building'), enabled })
}

export function useDemoBuildings() {
  return useQuery({ queryKey: userKeys.demoBuildings, queryFn: () => api<Building[]>('/buildings/demo') })
}

/** Role or building changed: everything the app shows depends on it. */
function useMeMutation<Body>(request: (body: Body) => Promise<Me>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (me) => {
      client.setQueryData(userKeys.me, me)
      void client.invalidateQueries()
    },
  })
}

export function useBindBuilding() {
  return useMeMutation((buildingCode: string) =>
    api<Me>('/me/residency', { method: 'PUT', body: JSON.stringify({ building_code: buildingCode }) }),
  )
}

/** DEMO_MODE: one MAX account walks both sides, resident and dispatcher. */
export function useBecomeDemoDispatcher() {
  return useMeMutation(() => api<Me>('/me/demo-dispatcher', { method: 'POST' }))
}

export function useForgetMe() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ detached_tickets: number }>('/me', { method: 'DELETE' }),
    onSuccess: () => client.resetQueries(),
  })
}
