import { Typography } from '@maxhub/max-ui'

import { useNavigation } from '@/app/navigationContext'
import { useMe } from '@/entities/user/api'

import { BuildingPicker } from './BuildingPicker'

export function BuildingsPage() {
  const { home } = useNavigation()
  const { data: me } = useMe()

  return (
    <div className="page">
      <header className="queue-head">
        <span className="muted small">{me?.residency ? 'Сейчас: ' + me.residency.address : 'Дом не выбран'}</span>
        <Typography.Headline variant="large-strong">🏠 Выберите ваш дом</Typography.Headline>
      </header>
      <BuildingPicker current={me?.residency?.building_code} onBound={home} />
    </div>
  )
}
