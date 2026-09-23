import { Button, Spinner, Typography } from '@maxhub/max-ui'
import type { ReactNode } from 'react'

import { ApiError } from '@/shared/api/client'

export function Loading() {
  return (
    <div className="state">
      <Spinner size={32} />
    </div>
  )
}

interface MessageProps {
  icon: string
  title: string
  text?: ReactNode
  action?: ReactNode
}

export function Message({ icon, title, text, action }: MessageProps) {
  return (
    <div className="state">
      <div className="state__icon">{icon}</div>
      <Typography.Title variant="medium-strong">{title}</Typography.Title>
      {text && <p className="muted state__text">{text}</p>}
      {action}
    </div>
  )
}

export function ErrorView({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : 'Не удалось загрузить данные'
  return (
    <Message
      icon="⚠️"
      title="Что-то пошло не так"
      text={message}
      action={
        onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            Повторить
          </Button>
        )
      }
    />
  )
}
