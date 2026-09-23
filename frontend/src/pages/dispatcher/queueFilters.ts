import type { Ticket } from '@/shared/api/client'

export type QueueFilter = 'all' | 'overdue' | 'emergency'

export const FILTER_LABELS: Record<QueueFilter, string> = {
  all: 'Все открытые',
  overdue: 'Просроченные',
  emergency: 'Аварийные',
}

export function applyFilter(tickets: Ticket[], filter: QueueFilter): Ticket[] {
  if (filter === 'overdue') return tickets.filter((ticket) => ticket.is_overdue)
  if (filter === 'emergency') return tickets.filter((ticket) => ticket.is_emergency)
  return tickets
}

export interface QueueStats {
  open: number
  overdue: number
  emergency: number
  buildings: number
}

export function queueStats(tickets: Ticket[]): QueueStats {
  return {
    open: tickets.length,
    overdue: tickets.filter((ticket) => ticket.is_overdue).length,
    emergency: tickets.filter((ticket) => ticket.is_emergency).length,
    buildings: new Set(tickets.map((ticket) => ticket.building_id)).size,
  }
}
