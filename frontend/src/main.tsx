import '@maxhub/max-ui/dist/styles.css'
import './styles.css'

import { MaxUI } from '@maxhub/max-ui'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/app/App'
import { NavigationProvider } from '@/app/navigation'
import { startScreens } from '@/app/startScreens'
import { ApiError } from '@/shared/api/client'
import { platform } from '@/shared/lib/bridge'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      // 4xx will not fix itself on retry; network hiccups might.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
})

const colorScheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MaxUI platform={platform()} colorScheme={colorScheme}>
      <QueryClientProvider client={queryClient}>
        <NavigationProvider initial={startScreens()}>
          <App />
        </NavigationProvider>
      </QueryClientProvider>
    </MaxUI>
  </StrictMode>,
)
