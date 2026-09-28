import { CellList, CellSimple } from '@maxhub/max-ui'

import { useNavigation } from '@/app/navigationContext'
import { useBecomeDemoDispatcher } from '@/entities/user/api'
import type { Me } from '@/shared/api/client'
import { haptic } from '@/shared/lib/bridge'

/** The rest of the bot's main menu: house tools, roles, privacy. */
export function HomeMenu({ me }: { me: Me }) {
  const { push } = useNavigation()
  const demoDispatcher = useBecomeDemoDispatcher()
  const hasHome = me.residency !== null

  return (
    <CellList mode="island" filled header={<span className="list-header">Ещё</span>}>
      {hasHome && (
        <MenuItem
          emoji="📊"
          title="Пульс дома"
          subtitle="Заявки за 30 дней и листовка с QR для соседей"
          onClick={() => push({ name: 'house' })}
        />
      )}
      <MenuItem
        emoji="🧭"
        title="Кто за что отвечает"
        subtitle="УО, ресурсники, капремонт, администрация"
        onClick={() => push({ name: 'guide' })}
      />
      {me.demo_mode && !me.dispatcher && (
        <MenuItem
          emoji="🧑‍💼"
          title="Демо: войти как диспетчер УО"
          subtitle={
            demoDispatcher.isError
              ? demoDispatcher.error.message
              : 'Очередь заявок всех домов УО и смена статусов'
          }
          disabled={demoDispatcher.isPending}
          onClick={() => {
            haptic.tap()
            demoDispatcher.mutate(undefined, { onSuccess: () => haptic.success(), onError: () => haptic.error() })
          }}
        />
      )}
      <MenuItem
        emoji="🏠"
        title={hasHome ? 'Сменить дом' : 'Выбрать дом'}
        onClick={() => push({ name: 'buildings' })}
      />
      <MenuItem emoji="🔒" title="Мои данные" onClick={() => push({ name: 'privacy' })} />
    </CellList>
  )
}

interface ItemProps {
  emoji: string
  title: string
  subtitle?: string
  disabled?: boolean
  onClick: () => void
}

function MenuItem({ emoji, title, subtitle, disabled, onClick }: ItemProps) {
  return (
    <CellSimple
      as="button"
      disabled={disabled}
      onClick={onClick}
      before={<span className="cell-emoji">{emoji}</span>}
      title={title}
      subtitle={subtitle}
      showChevron
    />
  )
}
