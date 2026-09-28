/**
 * The "problem -> draft" dialog as pure state transitions, the same steps as
 * the bot (backend/src/bot/handlers/create.py): quick category or own words,
 * clarifying questions, emergency check when the classifier is unsure, draft.
 * The server is stateless: every call gets the whole conversation.
 */

import type { CategoryRef, DraftStep, Triage, Turn } from '@/shared/api/client'

export type Phase = 'start' | 'asking' | 'emergency' | 'draft'

export interface IntakeState {
  phase: Phase
  turns: Turn[]
  /** Quick category the resident picked; after triage, the detected one. */
  category: string | null
  explanation: string
  draft: string | null
  triage: Triage | null
}

export const INITIAL: IntakeState = {
  phase: 'start',
  turns: [],
  category: null,
  explanation: '',
  draft: null,
  triage: null,
}

/** A quick category asks its own first question, no server round trip. */
export function startWithCategory(category: CategoryRef): IntakeState {
  return {
    ...INITIAL,
    phase: 'asking',
    category: category.code,
    turns: [
      { role: 'user', text: `Проблема: ${category.title}` },
      { role: 'bot', text: category.clarifying_question },
    ],
  }
}

export function withUserText(state: IntakeState, text: string): IntakeState {
  return { ...state, turns: [...state.turns, { role: 'user', text }] }
}

export function withStep(state: IntakeState, step: DraftStep): IntakeState {
  if (!step.ready || !step.draft || !step.triage) {
    const question = step.question ?? 'Расскажите, пожалуйста, подробнее.'
    return {
      ...state,
      phase: 'asking',
      explanation: step.explanation,
      turns: [...state.turns, { role: 'bot', text: question }],
    }
  }
  return {
    ...state,
    phase: step.triage.needs_emergency_confirmation ? 'emergency' : 'draft',
    explanation: step.explanation,
    draft: step.draft,
    triage: step.triage,
    category: step.triage.category_code,
  }
}

/** The resident answered "is it an emergency?": the deadline is recomputed. */
export function withTriage(state: IntakeState, triage: Triage): IntakeState {
  return { ...state, phase: 'draft', triage }
}

export function withDraft(state: IntakeState, draft: string): IntakeState {
  return { ...state, draft }
}

/** The last question the bot asked, shown above the answer field. */
export function lastQuestion(state: IntakeState): string | null {
  const last = state.turns.at(-1)
  return last?.role === 'bot' ? last.text : null
}
