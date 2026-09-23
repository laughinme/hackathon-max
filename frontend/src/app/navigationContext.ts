import { createContext, useContext } from 'react'

export type Screen = { name: 'home' } | { name: 'ticket'; id: string }

export interface Navigation {
  current: Screen
  push: (screen: Screen) => void
  pop: () => void
}

export const NavigationContext = createContext<Navigation | null>(null)

export function useNavigation(): Navigation {
  const navigation = useContext(NavigationContext)
  if (!navigation) throw new Error('useNavigation outside NavigationProvider')
  return navigation
}
