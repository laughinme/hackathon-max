import { Button, Typography } from '@maxhub/max-ui'

import { category, PARTY_LABELS } from '@/entities/ticket/labels'
import type { Triage } from '@/shared/api/client'
import { formatMoment } from '@/shared/lib/format'

import { AnswerField } from './AnswerField'

interface Props {
  draft: string
  triage: Triage
  refining: boolean
  submitting: boolean
  onFix: (comment: string, clear: () => void) => void
  onSubmit: () => void
  onRestart: () => void
}

/** What goes to the company and by when it must be fixed, before "Send". */
export function DraftReview({ draft, triage, refining, submitting, onFix, onSubmit, onRestart }: Props) {
  const { emoji, title } = category(triage.category_code)

  return (
    <>
      <section className="card">
        <Typography.Title variant="small-strong">📄 Черновик заявки</Typography.Title>
        <p className="prewrap">{draft}</p>
      </section>

      <section className={`card deadline ${triage.is_emergency ? 'deadline--emergency' : ''}`}>
        <dl className="facts">
          <dt>Категория</dt>
          <dd>
            {emoji} {title}
          </dd>
          <dt>Срочность</dt>
          <dd>{triage.is_emergency ? '⚠️ аварийная' : 'плановая'}</dd>
          <dt>Отвечает</dt>
          <dd>
            {PARTY_LABELS[triage.responsible_party]}
            <span className="muted"> · {triage.responsibility_basis}</span>
          </dd>
          {triage.react_by && (
            <>
              <dt>Реакция аварийной службы</dt>
              <dd>до {formatMoment(triage.react_by)}</dd>
            </>
          )}
          <dt>Срок устранения</dt>
          <dd>
            <b>до {formatMoment(triage.resolve_by)}</b>
          </dd>
          <dt>Основание срока</dt>
          <dd className="muted">{triage.deadline_basis}</dd>
        </dl>
        <p className="muted small">Срок считается от момента отправки.</p>
      </section>

      <section className="card actions">
        <Typography.Title variant="small-strong">Что-то не так?</Typography.Title>
        <AnswerField placeholder="Напишите, что поправить" action="Поправить" busy={refining} onSubmit={onFix} />
        <p className="muted small">Фото можно приложить, если оформлять заявку в чате с ботом.</p>
      </section>

      <div className="actions__buttons">
        <Button stretched size="large" loading={submitting} disabled={refining} onClick={onSubmit}>
          ✅ Отправить
        </Button>
        <Button stretched size="large" variant="secondary" disabled={submitting} onClick={onRestart}>
          🔄 Начать заново
        </Button>
      </div>
    </>
  )
}
