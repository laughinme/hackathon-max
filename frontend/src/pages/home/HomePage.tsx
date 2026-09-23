import { Button } from '@maxhub/max-ui'
import { useState } from 'react'

import { useMe } from '@/entities/user/api'
import { MyTicketsPage } from '@/pages/resident/MyTicketsPage'
import { QueuePage } from '@/pages/dispatcher/QueuePage'
import { NoAuthError } from '@/shared/api/client'
import { openMaxLink } from '@/shared/lib/bridge'
import { BOT_URL } from '@/shared/config'
import { ErrorView, Loading, Message } from '@/shared/ui/StateView'

type Tab = 'queue' | 'mine'

/** Role decides the start screen: dispatchers land on the queue. */
export function HomePage() {
  const { data: me, error, refetch, isPending } = useMe()
  const [tab, setTab] = useState<Tab>('queue')

  if (isPending) return <Loading />
  if (error instanceof NoAuthError) {
    return (
      <Message
        icon="🔒"
        title="Откройте приложение в MAX"
        text="Приложение работает только из чата с ботом: так мы знаем, чьи это заявки, без логинов и паролей."
      />
    )
  }
  if (error) return <ErrorView error={error} onRetry={() => void refetch()} />

  const toBot = (
    <Button size="large" onClick={() => openMaxLink(BOT_URL)}>
      Открыть чат с ботом
    </Button>
  )

  if (me.dispatcher && me.residency) {
    return (
      <>
        <div className="segmented" role="tablist">
          <SegmentButton active={tab === 'queue'} onClick={() => setTab('queue')}>
            Очередь УО
          </SegmentButton>
          <SegmentButton active={tab === 'mine'} onClick={() => setTab('mine')}>
            Мои заявки
          </SegmentButton>
        </div>
        {tab === 'queue' ? (
          <QueuePage companyName={me.dispatcher.company_name} />
        ) : (
          <MyTicketsPage residency={me.residency} />
        )}
      </>
    )
  }
  if (me.dispatcher) return <QueuePage companyName={me.dispatcher.company_name} />
  if (me.residency) return <MyTicketsPage residency={me.residency} />

  return (
    <Message
      icon="🏠"
      title="Сначала выберите дом"
      text="Отсканируйте QR-код в подъезде или выберите дом в чате с ботом. После этого здесь появятся ваши заявки."
      action={toBot}
    />
  )
}

function SegmentButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button role="tab" aria-selected={active} className={`segment ${active ? 'segment--active' : ''}`} onClick={onClick}>
      {children}
    </button>
  )
}
