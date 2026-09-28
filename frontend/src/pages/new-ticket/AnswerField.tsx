import { Button, Textarea } from '@maxhub/max-ui'
import { useState } from 'react'

interface Props {
  placeholder: string
  action: string
  busy: boolean
  /** Gets the text and a callback that clears the field once it is accepted. */
  onSubmit: (text: string, clear: () => void) => void
}

/** Free text in the resident's own words, like a message to the bot. */
export function AnswerField({ placeholder, action, busy, onSubmit }: Props) {
  const [text, setText] = useState('')
  const trimmed = text.trim()

  return (
    <div className="answer">
      <Textarea placeholder={placeholder} value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} />
      <Button
        stretched
        size="large"
        loading={busy}
        disabled={!trimmed || busy}
        onClick={() => onSubmit(trimmed, () => setText(''))}
      >
        {action}
      </Button>
    </div>
  )
}
