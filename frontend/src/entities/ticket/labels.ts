/** How ticket values read in the UI; mirrors backend/src/bot/presenters.py. */

import type { Schemas, TicketStatus } from '@/shared/api/client'

export const STATUS_LABELS: Record<TicketStatus, string> = {
  registered: 'Зарегистрирована',
  acknowledged: 'Принята УО',
  in_progress: 'В работе',
  done: 'Выполнена, ждёт подтверждения',
  confirmed: 'Закрыта',
  rejected: 'Отклонена',
}

export const STATUS_EMOJI: Record<TicketStatus, string> = {
  registered: '📥',
  acknowledged: '👀',
  in_progress: '🔧',
  done: '🏁',
  confirmed: '✅',
  rejected: '⛔️',
}

/** What the dispatcher's button says for moving a ticket to a status. */
export const STATUS_ACTIONS: Partial<Record<TicketStatus, string>> = {
  acknowledged: 'Принять заявку',
  in_progress: 'Взять в работу',
  done: 'Отметить выполненной',
  rejected: 'Отклонить',
}

export const CLOSED_STATUSES: ReadonlySet<TicketStatus> = new Set(['confirmed', 'rejected'])

export const CATEGORY_TITLES: Record<string, { emoji: string; title: string }> = {
  water: { emoji: '💧', title: 'Вода / протечка' },
  light: { emoji: '💡', title: 'Нет света' },
  heating: { emoji: '🔥', title: 'Отопление' },
  door: { emoji: '🚪', title: 'Дверь / домофон' },
  cleaning: { emoji: '🗑', title: 'Уборка / мусор' },
  lift: { emoji: '🛗', title: 'Лифт' },
  other: { emoji: '✍️', title: 'Другая проблема' },
}

export function category(code: string): { emoji: string; title: string } {
  return CATEGORY_TITLES[code] ?? { emoji: '✍️', title: 'Другая проблема' }
}

export const PARTY_LABELS: Record<Schemas['ResponsibleParty'], string> = {
  management_company: 'Управляющая организация',
  resource_supplier: 'Ресурсоснабжающая организация',
  capital_repair_operator: 'Региональный оператор капремонта',
  municipality: 'Администрация муниципалитета',
  owner: 'Собственник помещения',
}

export const ACTOR_LABELS: Record<Schemas['ActorRole'], string> = {
  resident: 'Житель',
  dispatcher: 'Диспетчер УО',
  system: 'Система',
}
