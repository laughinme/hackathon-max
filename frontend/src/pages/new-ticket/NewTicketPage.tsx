import { Button, Typography } from '@maxhub/max-ui'

import { useNavigation } from '@/app/navigationContext'
import { useIntake } from '@/features/intake/useIntake'

import { ChatStep } from './ChatStep'
import { DraftReview } from './DraftReview'
import { StartStep } from './StartStep'

/** "Сообщить о проблеме" from the bot, as a form: the same steps and texts. */
export function NewTicketPage() {
  const { replace } = useNavigation()
  const intake = useIntake((ticket) => replace({ name: 'ticket', id: ticket.id }))
  const { state } = intake

  return (
    <div className="page">
      <header className="queue-head">
        <span className="muted small">Новая заявка</span>
        <Typography.Headline variant="large-strong">📝 Сообщить о проблеме</Typography.Headline>
      </header>

      {state.phase === 'start' && (
        <StartStep thinking={intake.thinking} onText={intake.sendText} onCategory={intake.pickCategory} />
      )}

      {state.phase === 'asking' && (
        <>
          <ChatStep
            turns={state.turns}
            explanation={state.explanation}
            thinking={intake.thinking}
            onAnswer={intake.sendText}
          />
          <Button stretched size="medium" variant="ghost" onClick={intake.restart}>
            ⬅️ К быстрым сценариям
          </Button>
        </>
      )}

      {state.phase === 'emergency' && (
        <section className="card actions">
          <Typography.Title variant="small-strong">⚠️ Это авария?</Typography.Title>
          <p>
            Есть угроза людям или имуществу: топит, искрит, пахнет газом, кто-то застрял в лифте, нет воды или тепла
            во всём доме?
          </p>
          <p className="muted small">От ответа зависит нормативный срок: аварию устраняют быстрее.</p>
          <div className="actions__buttons">
            <Button
              stretched
              size="large"
              variant="destructive"
              disabled={intake.answering}
              onClick={() => intake.answerEmergency(true)}
            >
              ⚠️ Да, это авария
            </Button>
            <Button
              stretched
              size="large"
              variant="secondary"
              disabled={intake.answering}
              onClick={() => intake.answerEmergency(false)}
            >
              Нет, не срочно
            </Button>
          </div>
        </section>
      )}

      {state.phase === 'draft' && state.draft && state.triage && (
        <DraftReview
          draft={state.draft}
          triage={state.triage}
          refining={intake.refining}
          submitting={intake.submitting}
          onFix={intake.fixDraft}
          onSubmit={intake.submit}
          onRestart={intake.restart}
        />
      )}

      {intake.error && <p className="text-negative small center">{intake.error.message}</p>}
    </div>
  )
}
