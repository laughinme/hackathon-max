import { Typography } from '@maxhub/max-ui'

import type { Ticket } from '@/shared/api/client'
import { formatShort } from '@/shared/lib/format'

import { ACTOR_LABELS, STATUS_EMOJI, STATUS_LABELS } from './labels'

export function Timeline({ events }: { events: Ticket['events'] }) {
  return (
    <ol className="timeline">
      {events.map((event, index) => (
        <li key={`${event.at}-${index}`} className="timeline__item">
          <span className="timeline__dot">{STATUS_EMOJI[event.status]}</span>
          <div>
            <Typography.Body variant="medium-strong">{STATUS_LABELS[event.status]}</Typography.Body>
            <div className="muted small">
              {formatShort(event.at)} · {ACTOR_LABELS[event.actor_role]}
            </div>
            {event.comment && <div className="timeline__comment">«{event.comment}»</div>}
          </div>
        </li>
      ))}
    </ol>
  )
}
