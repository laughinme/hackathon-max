import { useQuery } from '@tanstack/react-query'

import { api, type CategoryRef, type GuideEntry } from '@/shared/api/client'

/** Reference data changes with a deploy, not during a session. */
const FOREVER = Number.POSITIVE_INFINITY

export function useCategories() {
  return useQuery({
    queryKey: ['reference', 'categories'],
    queryFn: () => api<CategoryRef[]>('/reference/categories'),
    staleTime: FOREVER,
  })
}

export function useGuide() {
  return useQuery({
    queryKey: ['reference', 'responsibility'],
    queryFn: () => api<GuideEntry[]>('/reference/responsibility'),
    staleTime: FOREVER,
  })
}
