import { Button, Typography } from '@maxhub/max-ui'

import { useEscalate } from '@/entities/ticket/api'
import type { Ticket } from '@/shared/api/client'
import { haptic, openMaxLink } from '@/shared/lib/bridge'
import { BOT_URL } from '@/shared/config'
import { formatMoment, formatTimeLeft } from '@/shared/lib/format'

/**
 * After the legal deadline the reporter can get a ready complaint to the
 * housing inspection: facts and timeline filled in, the bot sends the PDF.
 */
export function EscalateCard({ ticket }: { ticket: Ticket }) {
  const mutation = useEscalate(ticket.id)
  if (!ticket.can_escalate) return null

  const sent = mutation.isSuccess || ticket.escalated_at !== null

  const request = () => {
    haptic.tap()
    mutation.mutate({}, { onSuccess: () => haptic.success(), onError: () => haptic.error() })
  }

  return (
    <section className="card actions escalate">
      <Typography.Title variant="small-strong">🚨 Нормативный срок истёк</Typography.Title>
      <p className="text-negative small">Устранение {formatTimeLeft(ticket.resolve_by)}</p>
      <p className="muted">
        Управляющая организация не уложилась в нормативный срок. Жалоба в жилищную инспекцию уже заполнена
        фактами и историей заявки — останется вписать ФИО и адрес, подписать и подать. Ответ по закону — в течение
        30 дней.
      </p>
      {sent ? (
        <>
          <p className="small">
            📨 PDF отправлен в чат с ботом
            {ticket.escalated_at && ` · впервые ${formatMoment(ticket.escalated_at)}`}
          </p>
          <div className="actions__buttons">
            <Button stretched size="large" onClick={() => openMaxLink(BOT_URL)}>
              Открыть чат с документом
            </Button>
            <Button stretched size="large" variant="secondary" loading={mutation.isPending} onClick={request}>
              Прислать ещё раз
            </Button>
          </div>
        </>
      ) : (
        <Button stretched size="large" variant="destructive" loading={mutation.isPending} onClick={request}>
          📄 Подготовить жалобу в жилинспекцию
        </Button>
      )}
      {mutation.isError && <p className="text-negative small">{mutation.error.message}</p>}
    </section>
  )
}
