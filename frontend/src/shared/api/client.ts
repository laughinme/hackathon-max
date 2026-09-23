/**
 * Fetch client for the backend REST (docs/CONTRACTS.md §3).
 *
 * Auth is the signed MAX launch data: `Authorization: tma <initData>`, checked
 * by HMAC on the server. Outside MAX, `VITE_DEV_USER_ID` switches to
 * `dev <id>`, which the backend accepts only with DEV_AUTH_ENABLED=true.
 * Errors come as RFC 7807 problem+json with `error_code`.
 */

import { initData } from '@/shared/lib/bridge'

import type { components } from './schema'

export type Schemas = components['schemas']
export type Ticket = Schemas['TicketOut']
export type TicketStatus = Schemas['TicketStatus']
export type Me = Schemas['MeOut']
export type StatusChange = Schemas['StatusChangeIn']
export type Confirmation = Schemas['ConfirmationIn']

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export class NoAuthError extends ApiError {
  constructor() {
    super(401, 'no_init_data', 'Откройте приложение из чата с ботом в MAX')
  }
}

function authorization(): string {
  const data = initData()
  if (data) return `tma ${data}`
  const devUser = import.meta.env.VITE_DEV_USER_ID as string | undefined
  if (devUser) return `dev ${devUser}`
  throw new NoAuthError()
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      Authorization: authorization(),
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  if (response.ok) return (await response.json()) as T

  let code = 'http_error'
  let message = `Ошибка ${response.status}`
  try {
    const problem = (await response.json()) as { error_code?: string; detail?: unknown }
    code = problem.error_code ?? code
    if (typeof problem.detail === 'string') message = problem.detail
  } catch {
    // not a problem+json body: keep the generic message
  }
  throw new ApiError(response.status, code, message)
}
