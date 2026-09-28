import { CellList, CellSimple } from '@maxhub/max-ui'

import { useBindBuilding, useDemoBuildings } from '@/entities/user/api'
import { haptic } from '@/shared/lib/bridge'
import { ErrorView, Loading } from '@/shared/ui/StateView'

const QR_HINT =
  'В реальном доме ссылка на бота с кодом дома висит в подъезде в виде QR-кода, выбирать ничего не нужно.'

/** Demo buildings of the test company; the chosen one is saved for the bot too. */
export function BuildingPicker({ current, onBound }: { current?: string; onBound?: () => void }) {
  const { data: buildings, error, refetch, isPending } = useDemoBuildings()
  const bind = useBindBuilding()

  if (isPending) return <Loading />
  if (error) return <ErrorView error={error} onRetry={() => void refetch()} />

  const choose = (code: string) => {
    haptic.tap()
    bind.mutate(code, {
      onSuccess: () => {
        haptic.success()
        onBound?.()
      },
      onError: () => haptic.error(),
    })
  }

  return (
    <>
      <CellList
        mode="island"
        filled
        header={<span className="list-header">Демонстрационные дома УО «Комфорт», Псков</span>}
      >
        {buildings.map((building) => (
          <CellSimple
            key={building.code}
            as="button"
            disabled={bind.isPending}
            onClick={() => choose(building.code)}
            before={<span className="cell-emoji">🏠</span>}
            title={building.address}
            subtitle={building.code === current ? 'ваш дом сейчас' : undefined}
            showChevron
          />
        ))}
      </CellList>
      {bind.isError && <p className="text-negative small center">{bind.error.message}</p>}
      <p className="muted small center">{QR_HINT}</p>
    </>
  )
}
