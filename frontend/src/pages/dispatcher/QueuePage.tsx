import { CellList, Typography } from '@maxhub/max-ui'
import { useState } from 'react'

import { useNavigation } from '@/app/navigationContext'
import { useDispatcherQueue } from '@/entities/ticket/api'
import { CLOSED_STATUSES } from '@/entities/ticket/labels'
import { TicketCell } from '@/entities/ticket/TicketCell'
import { haptic } from '@/shared/lib/bridge'
import { ErrorView, Loading, Message } from '@/shared/ui/StateView'

import { applyFilter, FILTER_LABELS, type QueueFilter, queueStats } from './queueFilters'

export function QueuePage({ companyName }: { companyName: string }) {
  const { push } = useNavigation()
  const [filter, setFilter] = useState<QueueFilter>('all')
  const { data, error, refetch, isPending } = useDispatcherQueue()

  if (isPending) return <Loading />
  if (error) return <ErrorView error={error} onRetry={() => void refetch()} />

  const open = data.filter((ticket) => !CLOSED_STATUSES.has(ticket.status))
  const stats = queueStats(open)
  const visible = applyFilter(open, filter)

  return (
    <div className="page">
      <header className="queue-head">
        <span className="muted small">Диспетчерская</span>
        <Typography.Headline variant="large-strong">{companyName}</Typography.Headline>
      </header>

      <div className="stats">
        <Stat value={stats.open} label="открыто" />
        <Stat value={stats.overdue} label="просрочено" tone={stats.overdue ? 'negative' : undefined} />
        <Stat value={stats.emergency} label="аварийных" tone={stats.emergency ? 'warning' : undefined} />
        <Stat value={stats.buildings} label="домов" />
      </div>

      <div className="chips" role="tablist">
        {(Object.keys(FILTER_LABELS) as QueueFilter[]).map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={filter === key}
            className={`chip ${filter === key ? 'chip--active' : ''}`}
            onClick={() => {
              haptic.tap()
              setFilter(key)
            }}
          >
            {FILTER_LABELS[key]}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <Message icon="🎉" title="Здесь пусто" text="Заявок с таким фильтром нет." />
      ) : (
        <CellList mode="island" filled header={<span className="list-header">Сначала те, у кого срок ближе</span>}>
          {visible.map((ticket) => (
            <TicketCell key={ticket.id} ticket={ticket} showAddress onOpen={(id) => push({ name: 'ticket', id })} />
          ))}
        </CellList>
      )}
    </div>
  )
}

function Stat({ value, label, tone }: { value: number; label: string; tone?: 'negative' | 'warning' }) {
  return (
    <div className={`stat ${tone ? `stat--${tone}` : ''}`}>
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  )
}
