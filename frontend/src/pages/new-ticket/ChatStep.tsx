import type { Turn } from '@/shared/api/client'

import { AnswerField } from './AnswerField'

interface Props {
  turns: Turn[]
  explanation: string
  thinking: boolean
  onAnswer: (text: string, clear: () => void) => void
}

/** Clarifying questions as a short conversation, answers in the resident's words. */
export function ChatStep({ turns, explanation, thinking, onAnswer }: Props) {
  return (
    <section className="card">
      <ol className="chat">
        {turns.map((turn, index) => (
          <li key={index} className={`chat__bubble chat__bubble--${turn.role}`}>
            {turn.role === 'bot' && index === turns.length - 1 && explanation && (
              <span className="chat__explanation">{explanation}</span>
            )}
            {turn.text}
          </li>
        ))}
        {thinking && <li className="chat__bubble chat__bubble--bot muted">Разбираюсь…</li>}
      </ol>
      <AnswerField placeholder="Ваш ответ" action="Ответить" busy={thinking} onSubmit={onAnswer} />
    </section>
  )
}
