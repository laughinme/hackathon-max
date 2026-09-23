import type { TicketStatus } from '@/shared/api/client'

import { STATUS_EMOJI, STATUS_LABELS } from './labels'

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span className={`badge badge--${status}`}>
      {STATUS_EMOJI[status]} {STATUS_LABELS[status]}
    </span>
  )
}
