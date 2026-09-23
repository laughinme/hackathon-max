import { useMe } from '@/entities/user/api'
import { HomePage } from '@/pages/home/HomePage'
import { TicketPage } from '@/pages/ticket/TicketPage'

import { useNavigation } from './navigationContext'

export function App() {
  const { current } = useNavigation()
  const { data: me } = useMe()

  return (
    <main className="app">
      {current.name === 'ticket' ? <TicketPage key={current.id} id={current.id} /> : <HomePage />}
      {me?.demo_mode && (
        <footer className="demo-note">🧪 Тестовые данные: заявки не передаются в реальную управляющую организацию.</footer>
      )}
    </main>
  )
}
