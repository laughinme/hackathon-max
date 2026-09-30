import { Button, Typography } from '@maxhub/max-ui'
import { useMutation } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { category } from '@/entities/ticket/labels'
import { useHouse } from '@/entities/user/api'
import type { Pulse } from '@/shared/api/client'
import { downloadFile, haptic } from '@/shared/lib/bridge'
import { CountUp } from '@/shared/ui/CountUp'
import { ErrorView, Loading } from '@/shared/ui/StateView'

function hours(value: number): string {
  return value < 24 ? `${Math.round(value)} ч` : `${(value / 24).toFixed(1).replace('.', ',')} сут`
}

/** "Пульс дома" and the QR leaflet from the bot menu. */
export function HousePage() {
  const { data: house, error, refetch, isPending } = useHouse()
  const download = useMutation({
    mutationFn: ({ path, name }: { path: string; name: string }) => downloadFile(path, name),
    onSuccess: () => haptic.success(),
    onError: () => haptic.error(),
  })

  if (isPending) return <Loading />
  if (error) return <ErrorView error={error} onRetry={() => void refetch()} />

  return (
    <div className="page">
      <header className="queue-head">
        <Typography.Headline variant="large-strong">{house.address}</Typography.Headline>
        <span className="muted small">
          {house.company_name} · <a href={`tel:${house.company_phone}`}>{house.company_phone}</a>
        </span>
      </header>

      <PulseSection pulse={house.pulse} />

      <Group title="Листовка для соседей">
        <section className="card actions">
          <p className="muted">
            Распечатайте и повесьте у лифта или на двери: соседи отсканируют QR-код и сразу попадут в бота, уже
            привязанные к дому.
          </p>
          <Button
            stretched
            size="large"
            variant="secondary"
            loading={download.isPending}
            onClick={() => download.mutate({ path: house.leaflet_path, name: house.leaflet_filename })}
          >
            🖨 Скачать PDF с QR
          </Button>
          {download.isError && <p className="text-negative small">Не удалось скачать файл, попробуйте ещё раз.</p>}
        </section>
      </Group>
    </div>
  )
}

function Group({ title, footer, children }: { title: string; footer?: string; children: ReactNode }) {
  return (
    <section className="group">
      <span className="list-header">{title}</span>
      {children}
      {footer && <p className="group__footer">{footer}</p>}
    </section>
  )
}

function PulseSection({ pulse }: { pulse: Pulse }) {
  const title = `Пульс дома · ${pulse.period_days} дней`
  const footer = 'Считается по заявкам, поданным через «Домового».'

  if (pulse.total === 0) {
    return (
      <Group title={title} footer={footer}>
        <section className="card">
          <p className="muted">Заявок не было. Тихо — это хорошо.</p>
        </section>
      </Group>
    )
  }

  return (
    <Group title={title} footer={footer}>
      <div className="stats stats--three">
        <Stat value={pulse.total} label="заявок" />
        <Stat value={pulse.open} label="открыто" />
        <Stat value={pulse.overdue} label="просрочено" negative={pulse.overdue > 0} />
      </div>

      {(pulse.on_time_share !== null ||
        pulse.average_fix_hours !== null ||
        pulse.top_categories.length > 0 ||
        pulse.neighbours_joined > 0) && (
        <section className="card rows">
          {pulse.on_time_share !== null && <OnTimeRow pulse={pulse} share={pulse.on_time_share} />}
          {pulse.average_fix_hours !== null && (
            <div className="row">
              <span className="row__label">В среднем до устранения</span>
              <span className="row__value">{hours(pulse.average_fix_hours)}</span>
            </div>
          )}
          {pulse.neighbours_joined > 0 && (
            <div className="row">
              <span className="row__label">Соседи поддержали</span>
              <span className="row__value">{pulse.neighbours_joined} раз</span>
            </div>
          )}
          {pulse.top_categories.length > 0 && (
            <div className="row row--stack">
              <span className="row__label">Чаще всего</span>
              <div className="tags">
                {pulse.top_categories.map(({ category_code, count }) => {
                  const { emoji, title } = category(category_code)
                  return (
                    <span key={category_code} className="tag">
                      {emoji} {title}
                      <b className="tag__count">{count}</b>
                    </span>
                  )
                })}
              </div>
            </div>
          )}
        </section>
      )}
    </Group>
  )
}

function OnTimeRow({ pulse, share }: { pulse: Pulse; share: number }) {
  const percent = Math.round(share * 100)
  const tone = percent >= 80 ? 'positive' : percent >= 50 ? 'warning' : 'negative'
  return (
    <div className="row row--stack">
      <div className="row__line">
        <span className="row__label">В нормативный срок</span>
        <span className="row__value">
          <CountUp value={percent} />%
          <span className="muted">
            {' '}
            · {pulse.fixed_on_time} из {pulse.fixed}
          </span>
        </span>
      </div>
      <div className="meter" role="presentation">
        <div className={`meter__fill meter__fill--${tone}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function Stat({ value, label, negative = false }: { value: number; label: string; negative?: boolean }) {
  return (
    <div className={`stat ${negative ? 'stat--negative' : ''}`}>
      <span className="stat__value">
        <CountUp value={value} />
      </span>
      <span className="stat__label">{label}</span>
    </div>
  )
}
