import { Button, CellList, Typography } from '@maxhub/max-ui'

import { useNavigation } from '@/app/navigationContext'
import { useMyTickets } from '@/entities/ticket/api'
import { CLOSED_STATUSES } from '@/entities/ticket/labels'
import { TicketCell } from '@/entities/ticket/TicketCell'
import type { Me } from '@/shared/api/client'
import { openMaxLink } from '@/shared/lib/bridge'
import { BOT_URL } from '@/shared/config'
import { ErrorView, Loading, Message } from '@/shared/ui/StateView'

type Residency = NonNullable<Me['residency']>

export function MyTicketsPage({ residency }: { residency: Residency }) {
  const { push } = useNavigation()
  const { data: tickets, error, refetch, isPending } = useMyTickets()
  const open = (id: string) => push({ name: 'ticket', id })

  return (
    <div className="page">
      <section className="card home-card">
        <span className="muted small">Ваш дом</span>
        <Typography.Title variant="medium-strong">{residency.address}</Typography.Title>
        <span className="muted small">
          {residency.company_name} · <a href={`tel:${residency.company_phone}`}>{residency.company_phone}</a>
        </span>
        <Button stretched size="large" onClick={() => openMaxLink(BOT_URL)}>
          📝 Сообщить о проблеме
        </Button>
      </section>

      {isPending && <Loading />}
      {error && <ErrorView error={error} onRetry={() => void refetch()} />}
      {tickets && tickets.length === 0 && (
        <Message
          icon="📭"
          title="Заявок пока нет"
          text="Опишите проблему боту своими словами — он оформит заявку и назовёт нормативный срок."
        />
      )}
      {tickets && tickets.length > 0 && (
        <>
          <TicketGroup title="Открытые" tickets={tickets.filter((t) => !CLOSED_STATUSES.has(t.status))} onOpen={open} />
          <TicketGroup title="Закрытые" tickets={tickets.filter((t) => CLOSED_STATUSES.has(t.status))} onOpen={open} />
        </>
      )}
    </div>
  )
}

interface GroupProps {
  title: string
  tickets: NonNullable<ReturnType<typeof useMyTickets>['data']>
  onOpen: (id: string) => void
}

function TicketGroup({ title, tickets, onOpen }: GroupProps) {
  if (tickets.length === 0) return null
  return (
    <CellList mode="island" filled header={<span className="list-header">{title}</span>}>
      {tickets.map((ticket) => (
        <TicketCell key={ticket.id} ticket={ticket} onOpen={onOpen} />
      ))}
    </CellList>
  )
}
