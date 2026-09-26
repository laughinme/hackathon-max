/** Dates and deadlines in the resident's words, in Moscow time like the bot. */

const TIME_ZONE = 'Europe/Moscow'

const dayMonthTime = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: TIME_ZONE,
})

const shortDateTime = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: TIME_ZONE,
})

export function formatMoment(iso: string): string {
  return dayMonthTime.format(new Date(iso))
}

export function formatShort(iso: string): string {
  return shortDateTime.format(new Date(iso))
}

function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}

/** "2 дня 3 ч", "45 мин" — coarse on purpose, a deadline is not a stopwatch. */
export function formatDuration(ms: number): string {
  const minutes = Math.max(1, Math.round(Math.abs(ms) / 60_000))
  if (minutes < 60) return `${minutes} мин`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    const rest = minutes % 60
    return rest ? `${hours} ч ${rest} мин` : `${hours} ч`
  }
  const days = Math.floor(hours / 24)
  const restHours = hours % 24
  const daysText = `${days} ${plural(days, 'день', 'дня', 'дней')}`
  return restHours ? `${daysText} ${restHours} ч` : daysText
}

/** "осталось 5 ч" or "просрочено на 2 дня" relative to `now`. */
export function formatTimeLeft(deadlineIso: string, now: Date = new Date()): string {
  const left = new Date(deadlineIso).getTime() - now.getTime()
  return left >= 0
    ? `осталось ${formatDuration(left)}`
    : `просрочено на ${formatDuration(left)}`
}
