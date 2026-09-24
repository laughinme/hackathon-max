import { Typography } from '@maxhub/max-ui'

import { openLink } from '@/shared/lib/bridge'

/** Photos the resident attached in MAX; tap opens the full image. */
export function Photos({ urls }: { urls: string[] }) {
  if (urls.length === 0) return null
  return (
    <section className="card">
      <Typography.Title variant="small-strong">Фото</Typography.Title>
      <div className="photos">
        {urls.map((url) => (
          <button key={url} className="photos__item" onClick={() => openLink(url)}>
            <img src={url} alt="Фото от жителя" loading="lazy" />
          </button>
        ))}
      </div>
    </section>
  )
}
