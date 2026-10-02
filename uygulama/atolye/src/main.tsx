import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import './index.css'
import { TRPCProvider } from "@/providers/trpc"
import App from './App.tsx'
import { HataSiniri } from './components/HataSiniri'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Sınama A6: Atölye /atolye/ altında sunulur (vite base) — yönlendirici de oradan başlar. */}
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
      <TRPCProvider>
        <HataSiniri bolge="Uygulama">
          <App />
        </HataSiniri>
      </TRPCProvider>
    </BrowserRouter>
  </StrictMode>,
)
