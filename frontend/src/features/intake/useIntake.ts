import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { ticketKeys } from '@/entities/ticket/api'
import {
  api,
  type CategoryRef,
  type DraftStep,
  type Ticket,
  type TicketCreate,
  type Triage,
  type Turn,
} from '@/shared/api/client'
import { haptic } from '@/shared/lib/bridge'

import {
  INITIAL,
  type IntakeState,
  startWithCategory,
  withDraft,
  withStep,
  withTriage,
  withUserText,
} from './model'

const post = <T>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })

/** Dialog state plus the server calls behind each step. */
export function useIntake(onCreated: (ticket: Ticket) => void) {
  const client = useQueryClient()
  const [state, setState] = useState<IntakeState>(INITIAL)

  const analyze = useMutation({
    mutationFn: (body: { turns: Turn[]; category_code: string | null }) => post<DraftStep>('/intake/analyze', body),
  })
  const preview = useMutation({
    mutationFn: (body: { category_code: string; is_emergency: boolean }) => post<Triage>('/intake/preview', body),
  })
  const refine = useMutation({
    mutationFn: (body: { draft: string; comment: string }) => post<{ draft: string }>('/intake/refine', body),
  })
  const create = useMutation({
    mutationFn: (body: TicketCreate) => post<Ticket>('/tickets', body),
    onSuccess: (ticket) => {
      client.setQueryData(ticketKeys.one(ticket.id), ticket)
      void client.invalidateQueries({ queryKey: ticketKeys.all })
      haptic.success()
      onCreated(ticket)
    },
    onError: () => haptic.error(),
  })

  /** The field is cleared only on success: a failed call keeps the text to resend. */
  const sendText = (text: string, onSent: () => void) => {
    const next = withUserText(state, text)
    analyze.mutate(
      { turns: next.turns, category_code: next.category },
      {
        onSuccess: (step) => {
          setState(withStep(next, step))
          onSent()
        },
        onError: () => haptic.error(),
      },
    )
  }

  const answerEmergency = (isEmergency: boolean) => {
    if (!state.category) return
    haptic.tap()
    preview.mutate(
      { category_code: state.category, is_emergency: isEmergency },
      { onSuccess: (triage) => setState((current) => withTriage(current, triage)) },
    )
  }

  const fixDraft = (comment: string, onDone: () => void) => {
    if (!state.draft) return
    refine.mutate(
      { draft: state.draft, comment },
      {
        onSuccess: ({ draft }) => {
          setState((current) => withDraft(current, draft))
          onDone()
        },
      },
    )
  }

  const submit = () => {
    if (!state.draft || !state.triage || create.isPending) return
    haptic.tap()
    create.mutate({
      category_code: state.triage.category_code,
      is_emergency: state.triage.is_emergency,
      description: state.draft,
    })
  }

  const restart = () => {
    for (const mutation of [analyze, preview, refine, create]) mutation.reset()
    setState(INITIAL)
  }

  const failed = [analyze, preview, refine, create].find((mutation) => mutation.isError)

  return {
    state,
    pickCategory: (category: CategoryRef) => {
      haptic.tap()
      setState(startWithCategory(category))
    },
    sendText,
    answerEmergency,
    fixDraft,
    submit,
    restart,
    thinking: analyze.isPending,
    answering: preview.isPending,
    refining: refine.isPending,
    submitting: create.isPending,
    error: failed?.error ?? null,
  }
}
