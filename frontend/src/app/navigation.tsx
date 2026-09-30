/**
 * A screen stack instead of a URL router: a mini-app has no address bar, and
 * the stack maps one-to-one onto MAX's header Back button, which is shown
 * whenever there is somewhere to go back to.
 */

import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'

import { backButton } from '@/shared/lib/bridge'

import { type Direction, NavigationContext, type Screen } from './navigationContext'

const HOME: Screen = { name: 'home' }

export function NavigationProvider({ initial, children }: { initial: Screen[]; children: ReactNode }) {
  const [stack, setStack] = useState<Screen[]>(initial)
  const [direction, setDirection] = useState<Direction>('none')

  const push = useCallback((screen: Screen) => {
    setStack((current) => [...current, screen])
    setDirection('forward')
    window.scrollTo(0, 0)
  }, [])
  const pop = useCallback(() => {
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : current))
    setDirection('back')
  }, [])
  const replace = useCallback((screen: Screen) => {
    setStack((current) => [...current.slice(0, -1), screen])
    setDirection('forward')
    window.scrollTo(0, 0)
  }, [])
  const home = useCallback(() => {
    setStack([HOME])
    setDirection('back')
    window.scrollTo(0, 0)
  }, [])

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
  const depth = stack.length
  const value = useMemo(
    () => ({ current, depth, direction, push, pop, replace, home }),
    [current, depth, direction, push, pop, replace, home],
  )
  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>
}
