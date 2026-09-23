import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type Confirmation, type StatusChange, type Ticket } from '@/shared/api/client'

export const ticketKeys = {
  all: ['tickets'] as const,
  mine: () => [...ticketKeys.all, 'mine'] as const,
  queue: (includeClosed: boolean) => [...ticketKeys.all, 'queue', includeClosed] as const,
  one: (id: string) => [...ticketKeys.all, 'one', id] as const,
}

export function useMyTickets() {
  return useQuery({ queryKey: ticketKeys.mine(), queryFn: () => api<Ticket[]>('/tickets') })
}

export function useDispatcherQueue(includeClosed = false) {
  return useQuery({
    queryKey: ticketKeys.queue(includeClosed),
    queryFn: () => api<Ticket[]>(`/dispatcher/queue?include_closed=${includeClosed}`),
    refetchInterval: 30_000,
  })
}

export function useTicket(id: string) {
  return useQuery({ queryKey: ticketKeys.one(id), queryFn: () => api<Ticket>(`/tickets/${id}`) })
}

/** Mutations return the fresh ticket; lists refetch in the background. */
function useTicketMutation<Body>(id: string, path: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: Body) =>
      api<Ticket>(`/tickets/${id}/${path}`, { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: (ticket) => {
      client.setQueryData(ticketKeys.one(id), ticket)
      void client.invalidateQueries({ queryKey: ticketKeys.all })
    },
  })
}

export function useChangeStatus(id: string) {
  return useTicketMutation<StatusChange>(id, 'status')
}

export function useConfirmResolution(id: string) {
  return useTicketMutation<Confirmation>(id, 'confirmation')
}

/** The bot sends the complaint PDF to the reporter's chat (202, no body needed). */
export function useEscalate(id: string) {
  return useTicketMutation<Record<string, never>>(id, 'escalation')
}

/** DEMO_MODE: the deadline passes now; the overdue notice arrives in seconds. */
export function useDemoExpire(id: string) {
  return useTicketMutation<Record<string, never>>(id, 'demo/expire-deadline')
}
