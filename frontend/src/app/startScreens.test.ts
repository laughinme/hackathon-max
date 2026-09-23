import { describe, expect, it } from 'vitest'

import { startScreens } from './startScreens'

describe('startScreens', () => {
  it('opens home by default', () => {
    expect(startScreens(undefined)).toEqual([{ name: 'home' }])
  })

  it('opens a ticket from a deep link with home underneath', () => {
    expect(startScreens('t_abc-123')).toEqual([{ name: 'home' }, { name: 'ticket', id: 'abc-123' }])
  })

  it('ignores unknown payloads', () => {
    expect(startScreens('promo')).toEqual([{ name: 'home' }])
    expect(startScreens('t_')).toEqual([{ name: 'home' }])
  })
})
