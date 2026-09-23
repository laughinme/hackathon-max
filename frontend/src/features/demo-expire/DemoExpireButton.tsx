import { Button } from '@maxhub/max-ui'

import { useDemoExpire } from '@/entities/ticket/api'
import type { Ticket } from '@/shared/api/client'
import { haptic } from '@/shared/lib/bridge'

/**
 * Demo only: a legal deadline is a day or a week long, a checker has minutes.
 * The shift is recorded in the ticket history as a demo action.
 */
export function DemoExpireButton({ ticket }: { ticket: Ticket }) {
  const mutation = useDemoExpire(ticket.id)
  if (!ticket.demo_can_expire) return null

  return (
    <section className="demo-action">
      <Button
        stretched
        size="medium"
        variant="ghost"
        loading={mutation.isPending}
        onClick={() => {
          haptic.tap()
          mutation.mutate({}, { onSuccess: () => haptic.success(), onError: () => haptic.error() })
        }}
      >
        ⏩ Демо: срок истёк
      </Button>
      <p className="muted small">
        Сдвигает нормативный срок в прошлое, чтобы показать уведомление о просрочке и жалобу в жилинспекцию. Сдвиг
        будет виден в истории заявки.
      </p>
      {mutation.isError && <p className="text-negative small">{mutation.error.message}</p>}
    </section>
  )
}
