/**
 * Thin typed wrapper over MAX Bridge (`window.WebApp`, docs/max/.../bridge.md).
 *
 * Outside MAX (plain browser during development) `window.WebApp` is missing or
 * has empty `initData`; every helper degrades to a no-op instead of throwing.
 */

type ImpactStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'
type NotificationType = 'error' | 'success' | 'warning'

interface MaxWebApp {
  initData: string
  initDataUnsafe?: { start_param?: string; user?: { first_name?: string } }
  platform?: 'ios' | 'android' | 'desktop' | 'web'
  BackButton?: {
    show(): void
    hide(): void
    onClick(callback: () => void): void
    offClick(callback: () => void): void
  }
  HapticFeedback?: {
    impactOccurred(style: ImpactStyle): void
    notificationOccurred(type: NotificationType): void
  }
  openMaxLink?(url: string): void
  openLink?(url: string): void
}

declare global {
  interface Window {
    WebApp?: MaxWebApp
  }
}

function webApp(): MaxWebApp | undefined {
  return typeof window === 'undefined' ? undefined : window.WebApp
}

/** Signed launch data for `Authorization: tma <initData>`; empty outside MAX. */
export function initData(): string {
  return webApp()?.initData ?? ''
}

export function isInsideMax(): boolean {
  return initData() !== ''
}

/** `ios` / `android` for MAX UI styling; everything else looks like iOS. */
export function platform(): 'ios' | 'android' {
  return webApp()?.platform === 'android' ? 'android' : 'ios'
}

export function startParam(): string | undefined {
  return webApp()?.initDataUnsafe?.start_param || undefined
}

export const backButton = {
  show: () => webApp()?.BackButton?.show(),
  hide: () => webApp()?.BackButton?.hide(),
  onClick: (callback: () => void) => webApp()?.BackButton?.onClick(callback),
  offClick: (callback: () => void) => webApp()?.BackButton?.offClick(callback),
}

export const haptic = {
  tap: () => webApp()?.HapticFeedback?.impactOccurred('light'),
  success: () => webApp()?.HapticFeedback?.notificationOccurred('success'),
  error: () => webApp()?.HapticFeedback?.notificationOccurred('error'),
}

/** Opens an external link (MAX asks the user to confirm leaving the app). */
export function openLink(url: string): void {
  const app = webApp()
  if (app?.openLink) app.openLink(url)
  else window.open(url, '_blank', 'noopener')
}

/** Opens a `https://max.ru/...` link inside MAX, anything else in a browser. */
export function openMaxLink(url: string): void {
  const app = webApp()
  if (app?.openMaxLink) app.openMaxLink(url)
  else window.open(url, '_blank', 'noopener')
}
