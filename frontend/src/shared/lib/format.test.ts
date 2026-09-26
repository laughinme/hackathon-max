import { describe, expect, it } from 'vitest'

import { formatDuration, formatTimeLeft } from './format'

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

describe('formatDuration', () => {
  it.each([
    [30 * MINUTE, '30 мин'],
    [2 * HOUR, '2 ч'],
    [2 * HOUR + 15 * MINUTE, '2 ч 15 мин'],
    [1 * DAY, '1 день'],
    [3 * DAY + 4 * HOUR, '3 дня 4 ч'],
    [5 * DAY, '5 дней'],
    [21 * DAY, '21 день'],
  ])('%d ms → %s', (ms, text) => {
    expect(formatDuration(ms)).toBe(text)
  })

  it('never shows zero minutes', () => {
    expect(formatDuration(0)).toBe('1 мин')
  })
})

describe('formatTimeLeft', () => {
  const now = new Date('2026-09-23T12:00:00Z')

  it('counts down before the deadline', () => {
    expect(formatTimeLeft('2026-09-23T17:00:00Z', now)).toBe('осталось 5 ч')
  })

  it('says overdue after the deadline', () => {
    expect(formatTimeLeft('2026-09-21T12:00:00Z', now)).toBe('просрочено на 2 дня')
  })
})
