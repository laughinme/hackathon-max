/**
 * A screen stack instead of a URL router: a mini-app has no address bar, and
 * the stack maps one-to-one onto MAX's header Back button, which is shown
 * whenever there is somewhere to go back to.
 */

import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'

import { backButton } from '@/shared/lib/bridge'

import { NavigationContext, type Screen } from './navigationContext'

const HOME: Screen = { name: 'home' }

export function NavigationProvider({ initial, children }: { initial: Screen[]; children: ReactNode }) {
  const [stack, setStack] = useState<Screen[]>(initial)

  const push = useCallback((screen: Screen) => {
    setStack((current) => [...current, screen])
    window.scrollTo(0, 0)
  }, [])
  const pop = useCallback(() => setStack((current) => (current.length > 1 ? current.slice(0, -1) : current)), [])

  const canGoBack = stack.length > 1
  useEffect(() => {
    if (!canGoBack) {
      backButton.hide()
      return
    }
    backButton.show()
    backButton.onClick(pop)
    return () => backButton.offClick(pop)
  }, [canGoBack, pop])

  const current = stack.at(-1) ?? HOME
  const value = useMemo(() => ({ current, push, pop }), [current, push, pop])
  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>
}
