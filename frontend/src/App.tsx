import { Route, Routes } from 'react-router-dom'
import { AppHeader } from '@/components/layout/AppHeader'
import { IdentificationProvider } from '@/context/IdentificationContext'
import { ArchitecturePage } from '@/pages/ArchitecturePage'
import { CatalogPage } from '@/pages/CatalogPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { IdentifyPage } from '@/pages/IdentifyPage'
import { LandingPage } from '@/pages/LandingPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProductPage } from '@/pages/ProductPage'
import { ResultsPage } from '@/pages/ResultsPage'

export default function App() {
  return (
    <IdentificationProvider>
      <div className="flex min-h-screen flex-col bg-background">
        <AppHeader />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/identify" element={<IdentifyPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/product/:sku" element={<ProductPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </IdentificationProvider>
  )
}
