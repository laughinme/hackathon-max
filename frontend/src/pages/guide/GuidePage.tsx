import { Typography } from '@maxhub/max-ui'

import { useGuide } from '@/entities/reference/api'
import { ErrorView, Loading } from '@/shared/ui/StateView'

/** "Кто за что отвечает": so a resident is not bounced between organisations. */
export function GuidePage() {
  const { data: guide, error, refetch, isPending } = useGuide()

  return (
    <div className="page">
      <header className="queue-head">
        <span className="muted small">Навигатор ответственности</span>
        <Typography.Headline variant="large-strong">🧭 Кто за что отвечает</Typography.Headline>
      </header>
      {isPending && <Loading />}
      {error && <ErrorView error={error} onRetry={() => void refetch()} />}
      {guide?.map((entry) => (
        <section key={entry.situation} className="card">
          <Typography.Title variant="small-strong">
            {entry.emoji} {entry.situation}
          </Typography.Title>
          <p>
            → <b>{entry.who}</b> <span className="muted small">({entry.basis})</span>
          </p>
          <p className="muted small">Куда: {entry.where}</p>
        </section>
      ))}
    </div>
  )
}
