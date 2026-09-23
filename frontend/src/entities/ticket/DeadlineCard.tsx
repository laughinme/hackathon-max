import { Typography } from '@maxhub/max-ui'

import type { Ticket } from '@/shared/api/client'
import { formatMoment, formatTimeLeft } from '@/shared/lib/format'

import { CLOSED_STATUSES, PARTY_LABELS } from './labels'

/** The legal deadline and who answers for it: the core promise of the product. */
export function DeadlineCard({ ticket }: { ticket: Ticket }) {
  const open = !CLOSED_STATUSES.has(ticket.status)
  const tone = ticket.is_overdue ? 'deadline--overdue' : ticket.is_emergency ? 'deadline--emergency' : ''

  return (
    <section className={`card deadline ${tone}`}>
      {open && (
        <Typography.Title variant="medium-strong" className="deadline__left">
          {ticket.is_overdue ? '🚨 ' : '⏱ '}
          {formatTimeLeft(ticket.resolve_by)}
        </Typography.Title>
      )}
      <dl className="facts">
        {ticket.react_by && (
          <>
            <dt>Реакция аварийной службы</dt>
            <dd>до {formatMoment(ticket.react_by)}</dd>
          </>
        )}
        <dt>Срок устранения</dt>
        <dd>до {formatMoment(ticket.resolve_by)}</dd>
        <dt>Основание срока</dt>
        <dd className="muted">{ticket.deadline_basis}</dd>
        <dt>Отвечает</dt>
        <dd>
          {PARTY_LABELS[ticket.responsible_party]}
          <span className="muted"> · {ticket.responsibility_basis}</span>
        </dd>
      </dl>
    </section>
  )
}
