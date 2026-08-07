import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
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

/**
 * SPA navigation keeps the scroll position of the page you left, so picking a
 * candidate deep down /results used to land mid-page on /product. Hash links
 * ("How It Works") are left to the browser's own anchor scrolling.
 */
function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (!hash) window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}

export default function App() {
  return (
    <IdentificationProvider>
      <ScrollToTop />
      {/* Transparent shell: the page atmosphere (aurora + star-field) is
          painted once on `body` and shows through on every route. */}
      <div className="flex min-h-screen flex-col">
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
