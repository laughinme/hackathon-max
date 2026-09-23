import { Button, Textarea, Typography } from '@maxhub/max-ui'
import { useState } from 'react'

import { useConfirmResolution } from '@/entities/ticket/api'
import type { Ticket } from '@/shared/api/client'
import { haptic } from '@/shared/lib/bridge'

/** The reporter closes the ticket or sends it back to work with a reason. */
export function ConfirmResolution({ ticket }: { ticket: Ticket }) {
  const mutation = useConfirmResolution(ticket.id)
  const [reopening, setReopening] = useState(false)
  const [comment, setComment] = useState('')
  if (!ticket.can_confirm) return null

  const send = (resolved: boolean) => {
    haptic.tap()
    mutation.mutate(
      { resolved, comment: comment.trim() || null },
      { onSuccess: () => haptic.success(), onError: () => haptic.error() },
    )
  }

  return (
    <section className="card actions">
      <Typography.Title variant="small-strong">УО отметила заявку выполненной. Всё работает?</Typography.Title>
      {reopening ? (
        <>
          <Textarea
            placeholder="Что осталось не так?"
            value={comment}
            maxLength={500}
            onChange={(event) => setComment(event.target.value)}
          />
          <Button
            stretched
            size="large"
            variant="destructive"
            loading={mutation.isPending}
            disabled={!comment.trim()}
            onClick={() => send(false)}
          >
            Вернуть в работу
          </Button>
        </>
      ) : (
        <div className="actions__buttons">
          <Button stretched size="large" loading={mutation.isPending} onClick={() => send(true)}>
            Да, всё работает
          </Button>
          <Button stretched size="large" variant="secondary" onClick={() => setReopening(true)}>
            Нет, не починили
          </Button>
        </div>
      )}
      {mutation.isError && <p className="text-negative small">{mutation.error.message}</p>}
    </section>
  )
}
