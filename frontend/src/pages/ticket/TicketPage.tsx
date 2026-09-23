import { Typography } from '@maxhub/max-ui'

import { DeadlineCard } from '@/entities/ticket/DeadlineCard'
import { useTicket } from '@/entities/ticket/api'
import { category } from '@/entities/ticket/labels'
import { StatusBadge } from '@/entities/ticket/StatusBadge'
import { Timeline } from '@/entities/ticket/Timeline'
import { ChangeStatusActions } from '@/features/change-status/ChangeStatusActions'
import { ConfirmResolution } from '@/features/confirm-resolution/ConfirmResolution'
import { EscalateCard } from '@/features/escalate/EscalateCard'
import { formatMoment } from '@/shared/lib/format'
import { ErrorView, Loading } from '@/shared/ui/StateView'

export function TicketPage({ id }: { id: string }) {
  const { data: ticket, error, refetch, isPending } = useTicket(id)
  if (isPending) return <Loading />
  if (error) return <ErrorView error={error} onRetry={() => void refetch()} />

  const { emoji, title } = category(ticket.category_code)
  const residentCanConfirm = ticket.available_statuses.includes('confirmed')

  return (
    <div className="page">
      <header className="ticket-head">
        <span className="muted small">
          № {ticket.number} · создана {formatMoment(ticket.created_at)}
        </span>
        <Typography.Headline variant="large-strong">
          {emoji} {title}
        </Typography.Headline>
        <div className="ticket-head__badges">
          <StatusBadge status={ticket.status} />
          {ticket.is_emergency && <span className="badge badge--emergency">⚠️ Авария</span>}
          {ticket.escalated_at && <span className="badge badge--escalated">📨 Жалоба в жилинспекцию</span>}
        </div>
      </header>

      <EscalateCard ticket={ticket} />
      {residentCanConfirm ? <ConfirmResolution ticket={ticket} /> : <ChangeStatusActions ticket={ticket} />}

      <DeadlineCard ticket={ticket} />

      <section className="card">
        <Typography.Title variant="small-strong">Описание</Typography.Title>
        <p className="prewrap">{ticket.description}</p>
        <p className="muted small">📍 {ticket.building_address}</p>
      </section>

      <section className="card">
        <Typography.Title variant="small-strong">История</Typography.Title>
        <Timeline events={ticket.events} />
      </section>
    </div>
  )
}
