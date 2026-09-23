import { startParam } from '@/shared/lib/bridge'

import type { Screen } from './navigationContext'

/** Prefix of `https://max.ru/<bot>?startapp=t_<ticket id>`: open one ticket. */
const TICKET_PREFIX = 't_'

/** Initial screen stack; a deep link to a ticket keeps Home underneath it. */
export function startScreens(param: string | undefined = startParam()): Screen[] {
  if (param?.startsWith(TICKET_PREFIX)) {
    const id = param.slice(TICKET_PREFIX.length)
    if (id) return [{ name: 'home' }, { name: 'ticket', id }]
  }
  return [{ name: 'home' }]
}
