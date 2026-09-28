import { Button, Typography } from '@maxhub/max-ui'
import { useState } from 'react'

import { useNavigation } from '@/app/navigationContext'
import { useForgetMe } from '@/entities/user/api'
import { haptic } from '@/shared/lib/bridge'
import { Message } from '@/shared/ui/StateView'

/** What the service stores and deleting it on request (as /privacy in the bot). */
export function PrivacyPage() {
  const { home } = useNavigation()
  const forget = useForgetMe()
  const [confirming, setConfirming] = useState(false)

  if (forget.isSuccess) {
    const detached = forget.data.detached_tickets
    return (
      <Message
        icon="✅"
        title="Данные удалены"
        text={detached ? `Заявок, отвязанных от вас: ${detached}.` : undefined}
        action={
          <Button size="large" onClick={home}>
            На главную
          </Button>
        }
      />
    )
  }

  return (
    <div className="page">
      <header className="queue-head">
        <span className="muted small">Конфиденциальность</span>
        <Typography.Headline variant="large-strong">🔒 Ваши данные</Typography.Headline>
      </header>

      <section className="card">
        <Typography.Title variant="small-strong">Что я храню</Typography.Title>
        <ul className="plain-list">
          <li>ваш идентификатор в MAX и имя из профиля — чтобы знать, чьи это заявки;</li>
          <li>дом, который вы выбрали, и роль (житель или диспетчер УО);</li>
          <li>тексты заявок и историю их статусов;</li>
          <li>черновик заявки, пока вы оформляете её в чате с ботом.</li>
        </ul>
        <p className="muted small">
          Телефон, адрес квартиры и паспортные данные я не запрашиваю. В жалобе в жилинспекцию ФИО и адрес вы
          вписываете сами, у меня они не остаются.
        </p>
      </section>

      <section className="card">
        <Typography.Title variant="small-strong">Зачем</Typography.Title>
        <p>Передать заявку в управляющую организацию, посчитать нормативный срок и сообщать вам о статусе.</p>
      </section>

      <section className="card actions">
        <Typography.Title variant="small-strong">Удаление</Typography.Title>
        <p>
          Отвяжу вас от дома и ролей. Заявки останутся у УО как обращения по дому, но без связи с вами — уведомлений
          по ним вы больше не получите. Черновик в чате с ботом стирается там же: команда /privacy.
        </p>
        {confirming ? (
          <>
            <p className="text-negative">Удалить мои данные? Отменить это нельзя.</p>
            <div className="actions__buttons">
              <Button
                stretched
                size="large"
                variant="destructive"
                loading={forget.isPending}
                onClick={() => {
                  haptic.tap()
                  forget.mutate(undefined, { onError: () => haptic.error() })
                }}
              >
                Да, удалить
              </Button>
              <Button stretched size="large" variant="secondary" onClick={() => setConfirming(false)}>
                Отмена
              </Button>
            </div>
          </>
        ) : (
          <Button stretched size="large" variant="destructive" onClick={() => setConfirming(true)}>
            🗑 Удалить мои данные
          </Button>
        )}
        {forget.isError && <p className="text-negative small">{forget.error.message}</p>}
      </section>
    </div>
  )
}
