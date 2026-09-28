import { useMe } from '@/entities/user/api'
import { BuildingsPage } from '@/pages/buildings/BuildingsPage'
import { GuidePage } from '@/pages/guide/GuidePage'
import { HomePage } from '@/pages/home/HomePage'
import { HousePage } from '@/pages/house/HousePage'
import { NewTicketPage } from '@/pages/new-ticket/NewTicketPage'
import { PrivacyPage } from '@/pages/privacy/PrivacyPage'
import { TicketPage } from '@/pages/ticket/TicketPage'

import { type Screen, useNavigation } from './navigationContext'

function ScreenView({ screen }: { screen: Screen }) {
  switch (screen.name) {
    case 'ticket':
      return <TicketPage key={screen.id} id={screen.id} />
    case 'new-ticket':
      return <NewTicketPage />
    case 'buildings':
      return <BuildingsPage />
    case 'house':
      return <HousePage />
    case 'guide':
      return <GuidePage />
    case 'privacy':
      return <PrivacyPage />
    case 'home':
      return <HomePage />
  }
}

export function App() {
  const { current } = useNavigation()
  const { data: me } = useMe()

  return (
    <main className="app">
      <ScreenView screen={current} />
      {me?.demo_mode && (
        <footer className="demo-note">🧪 Тестовые данные: заявки не передаются в реальную управляющую организацию.</footer>
      )}
    </main>
  )
}
