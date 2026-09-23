import { Button, Textarea, Typography } from '@maxhub/max-ui'
import { useState } from 'react'

import { useChangeStatus } from '@/entities/ticket/api'
import { STATUS_ACTIONS } from '@/entities/ticket/labels'
import type { StatusChange, Ticket } from '@/shared/api/client'
import { haptic } from '@/shared/lib/bridge'

type Target = StatusChange['status']

const TARGETS: readonly Target[] = ['acknowledged', 'in_progress', 'done', 'rejected']

function isTarget(status: string): status is Target {
  return (TARGETS as readonly string[]).includes(status)
}

/** Dispatcher moves the ticket; the resident gets the comment in the bot. */
export function ChangeStatusActions({ ticket }: { ticket: Ticket }) {
  const mutation = useChangeStatus(ticket.id)
  const [comment, setComment] = useState('')
  const targets = ticket.available_statuses.filter(isTarget)
  if (targets.length === 0) return null

  const submit = (status: Target) => {
    haptic.tap()
    mutation.mutate(
      { status, comment: comment.trim() || null },
      {
        onSuccess: () => {
          haptic.success()
          setComment('')
        },
        onError: () => haptic.error(),
      },
    )
  }

  return (
    <section className="card actions">
      <Typography.Title variant="small-strong">Действия диспетчера</Typography.Title>
      <Textarea
        placeholder="Комментарий для жителя: что сделано, когда придёт мастер"
        value={comment}
        maxLength={500}
        onChange={(event) => setComment(event.target.value)}
      />
      <div className="actions__buttons">
        {targets.map((status) => (
          <Button
            key={status}
            stretched
            size="large"
            variant={status === 'rejected' ? 'destructive' : status === targets[0] ? 'primary' : 'secondary'}
            loading={mutation.isPending && mutation.variables?.status === status}
            disabled={mutation.isPending || (status === 'rejected' && !comment.trim())}
            onClick={() => submit(status)}
          >
            {STATUS_ACTIONS[status]}
          </Button>
        ))}
      </div>
      {targets.includes('rejected') && !comment.trim() && (
        <p className="muted small">Чтобы отклонить заявку, напишите жителю причину.</p>
      )}
      {mutation.isError && <p className="text-negative small">{mutation.error.message}</p>}
    </section>
  )
}
