import { createContext, useContext } from 'react'

export type Screen =
  | { name: 'home' }
  | { name: 'ticket'; id: string }
  | { name: 'new-ticket' }
  | { name: 'buildings' }
  | { name: 'house' }
  | { name: 'guide' }
  | { name: 'privacy' }

export interface Navigation {
  current: Screen
  push: (screen: Screen) => void
  pop: () => void
  /** Swap the current screen, e.g. the finished form for the new ticket. */
  replace: (screen: Screen) => void
  /** Back to the start screen, e.g. after the building changed. */
  home: () => void
}

export const NavigationContext = createContext<Navigation | null>(null)

export function useNavigation(): Navigation {
  const navigation = useContext(NavigationContext)
  if (!navigation) throw new Error('useNavigation outside NavigationProvider')
  return navigation
}
