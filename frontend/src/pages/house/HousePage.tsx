import { Button, Typography } from '@maxhub/max-ui'
import { useMutation } from '@tanstack/react-query'

import { category } from '@/entities/ticket/labels'
import { useHouse } from '@/entities/user/api'
import type { Pulse } from '@/shared/api/client'
import { downloadFile, haptic } from '@/shared/lib/bridge'
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
        <span className="muted small">
          {house.company_name} · <a href={`tel:${house.company_phone}`}>{house.company_phone}</a>
        </span>
        <Typography.Headline variant="large-strong">{house.address}</Typography.Headline>
      </header>

      <PulseCard pulse={house.pulse} />

      <section className="card actions">
        <Typography.Title variant="small-strong">📣 Листовка с QR для соседей</Typography.Title>
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
          🖨 Скачать PDF
        </Button>
        {download.isError && <p className="text-negative small">Не удалось скачать файл, попробуйте ещё раз.</p>}
      </section>
    </div>
  )
}

function PulseCard({ pulse }: { pulse: Pulse }) {
  const onTime = pulse.on_time_share
  return (
    <section className="card">
      <Typography.Title variant="small-strong">📊 Пульс дома · за {pulse.period_days} дней</Typography.Title>
      {pulse.total === 0 ? (
        <p className="muted">Заявок не было. Тихо — это хорошо.</p>
      ) : (
        <>
          <div className="stats stats--three">
            <Stat value={String(pulse.total)} label="заявок" />
            <Stat value={String(pulse.open)} label="открыто" />
            <Stat value={String(pulse.overdue)} label="просрочено" negative={pulse.overdue > 0} />
          </div>
          <dl className="facts">
            {onTime !== null && (
              <>
                <dt>В нормативный срок</dt>
                <dd>
                  <b>{Math.round(onTime * 100)}%</b>
                  <span className="muted">
                    {' '}
                    · {pulse.fixed_on_time} из {pulse.fixed}
                  </span>
                </dd>
              </>
            )}
            {pulse.average_fix_hours !== null && (
              <>
                <dt>В среднем до устранения</dt>
                <dd>{hours(pulse.average_fix_hours)}</dd>
              </>
            )}
            {pulse.top_categories.length > 0 && (
              <>
                <dt>Чаще всего</dt>
                <dd>
                  {pulse.top_categories
                    .map(({ category_code, count }) => {
                      const { emoji, title } = category(category_code)
                      return `${emoji} ${title.toLowerCase()} — ${count}`
                    })
                    .join(', ')}
                </dd>
              </>
            )}
            {pulse.neighbours_joined > 0 && (
              <>
                <dt>Соседи поддержали</dt>
                <dd>{pulse.neighbours_joined} раз</dd>
              </>
            )}
          </dl>
        </>
      )}
      <p className="muted small">Считается по заявкам, поданным через «Домового».</p>
    </section>
  )
}

function Stat({ value, label, negative = false }: { value: string; label: string; negative?: boolean }) {
  return (
    <div className={`stat stat--inset ${negative ? 'stat--negative' : ''}`}>
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  )
}
