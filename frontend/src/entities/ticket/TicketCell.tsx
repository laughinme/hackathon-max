import { CellSimple } from '@maxhub/max-ui'

import type { Ticket } from '@/shared/api/client'
import { formatTimeLeft } from '@/shared/lib/format'

import { CLOSED_STATUSES, category, STATUS_EMOJI, STATUS_LABELS } from './labels'

interface Props {
  ticket: Ticket
  onOpen: (id: string) => void
  /** Dispatcher sees the address: the queue spans many buildings. */
  showAddress?: boolean
}

export function TicketCell({ ticket, onOpen, showAddress = false }: Props) {
  const { emoji, title } = category(ticket.category_code)
  const closed = CLOSED_STATUSES.has(ticket.status)
  const deadline = closed ? STATUS_LABELS[ticket.status] : formatTimeLeft(ticket.resolve_by)

  return (
    <CellSimple
      as="button"
      onClick={() => onOpen(ticket.id)}
      before={<span className="cell-emoji">{emoji}</span>}
      overline={`№ ${ticket.number}${ticket.is_emergency ? ' · ⚠️ авария' : ''}${
        ticket.supporters_count ? ` · 👥 ${ticket.supporters_count + 1}` : ''
      }${ticket.escalated_at ? ' · 📨 жалоба' : ''}`}
      title={showAddress ? ticket.building_address : title}
      subtitle={
        <span className={ticket.is_overdue ? 'text-negative' : undefined}>
          {STATUS_EMOJI[ticket.status]} {deadline}
        </span>
      }
      showChevron
    />
  )
}
