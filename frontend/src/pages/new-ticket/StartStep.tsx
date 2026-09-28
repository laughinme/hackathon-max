import { Typography } from '@maxhub/max-ui'

import { useCategories } from '@/entities/reference/api'
import type { CategoryRef } from '@/shared/api/client'
import { ErrorView, Loading } from '@/shared/ui/StateView'

import { AnswerField } from './AnswerField'

interface Props {
  thinking: boolean
  onText: (text: string, clear: () => void) => void
  onCategory: (category: CategoryRef) => void
}

/** Own words first; quick categories are shortcuts, not a required catalogue. */
export function StartStep({ thinking, onText, onCategory }: Props) {
  const { data: categories, error, refetch, isPending } = useCategories()

  return (
    <>
      <section className="card">
        <Typography.Title variant="small-strong">Что случилось?</Typography.Title>
        <p className="muted small">
          Опишите обычными словами, где и что: «течёт труба в подвале, второй подъезд». Я уточню детали, определю,
          кто отвечает, и покажу срок по нормативу.
        </p>
        <AnswerField placeholder="Опишите проблему" action="Дальше" busy={thinking} onSubmit={onText} />
      </section>

      <span className="list-header">Или быстрый сценарий</span>
      {isPending && <Loading />}
      {error && <ErrorView error={error} onRetry={() => void refetch()} />}
      {categories && (
        <div className="category-grid">
          {categories.map((category) => (
            <button
              key={category.code}
              className="category-grid__item"
              disabled={thinking}
              onClick={() => onCategory(category)}
            >
              <span className="category-grid__emoji">{category.emoji}</span>
              {category.title}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
