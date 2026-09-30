import { useLayoutEffect, useRef } from 'react'

const DURATION_MS = 700

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function CountUp({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const shown = useRef(0)

  useLayoutEffect(() => {
    const node = ref.current
    if (!node) return
    const from = shown.current
    if (from === value || prefersReducedMotion()) {
      shown.current = value
      node.textContent = String(value)
      return
    }

    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const progress = Math.min((now - start) / DURATION_MS, 1)
      const eased = 1 - (1 - progress) ** 3
      shown.current = Math.round(from + (value - from) * eased)
      node.textContent = String(shown.current)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    node.textContent = String(from)
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value])

  return <span ref={ref} />
}
