import { describe, expect, it } from 'vitest'

import type { DraftStep, Triage } from '@/shared/api/client'

import { INITIAL, lastQuestion, startWithCategory, withStep, withTriage, withUserText } from './model'

const lift = { code: 'lift', emoji: '🛗', title: 'Лифт', clarifying_question: 'Какой подъезд?' }

const triage = (overrides: Partial<Triage> = {}): Triage => ({
  category_code: 'water',
  is_emergency: true,
  needs_emergency_confirmation: false,
  responsible_party: 'management_company',
  responsibility_basis: 'ЖК РФ ст. 161',
  resolve_by: '2026-09-24T12:00:00+03:00',
  react_by: null,
  deadline_basis: 'Правила № 170',
  ...overrides,
})

const ready = (t: Triage): DraftStep => ({ ready: true, explanation: '', question: null, draft: 'Текст', triage: t })

describe('intake dialog', () => {
  it('a quick category asks its own question first', () => {
    const state = startWithCategory(lift)
    expect(state.phase).toBe('asking')
    expect(state.category).toBe('lift')
    expect(lastQuestion(state)).toBe('Какой подъезд?')
  })

  it('keeps asking while the server needs details', () => {
    const asked = withStep(withUserText(INITIAL, 'Течёт'), {
      ready: false,
      explanation: 'Похоже на протечку',
      question: 'Где именно?',
      draft: null,
      triage: null,
    })
    expect(asked.phase).toBe('asking')
    expect(asked.turns.map((t) => t.role)).toEqual(['user', 'bot'])
    expect(lastQuestion(asked)).toBe('Где именно?')
  })

  it('takes the detected category and shows the draft', () => {
    const state = withStep(withUserText(INITIAL, 'Течёт в подвале'), ready(triage()))
    expect(state.phase).toBe('draft')
    expect(state.category).toBe('water')
    expect(lastQuestion(state)).toBeNull()
  })

  it('asks about an emergency when the classifier is unsure', () => {
    const unsure = withStep(INITIAL, ready(triage({ needs_emergency_confirmation: true })))
    expect(unsure.phase).toBe('emergency')
    const answered = withTriage(unsure, triage({ is_emergency: false }))
    expect(answered.phase).toBe('draft')
    expect(answered.triage?.is_emergency).toBe(false)
  })
})
