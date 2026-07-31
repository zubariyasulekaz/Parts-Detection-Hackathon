import { Search } from 'lucide-react'
import type { MouseEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { LogoMark } from '@/components/common/LogoMark'

const NAV_LINK_CLASS =
  'text-sm font-medium text-muted transition-colors hover:text-foreground data-[active=true]:text-foreground'

export function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()

  function handleHowItWorksClick(event: MouseEvent<HTMLAnchorElement>) {
    if (location.pathname === '/') {
      event.preventDefault()
      document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else {
      event.preventDefault()
      navigate('/#how-it-works')
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-6 lg:px-10">
        <Link to="/" className="flex items-center gap-2.5" aria-label="PartPilot home">
          <LogoMark />
          <span className="text-[17px] font-bold tracking-tight text-foreground">PartPilot</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          <a href="/#how-it-works" onClick={handleHowItWorksClick} className={NAV_LINK_CLASS}>
            How It Works
          </a>
          <NavLink to="/catalog" className={NAV_LINK_CLASS} data-active={location.pathname === '/catalog'}>
            Catalog
          </NavLink>
          <NavLink to="/architecture" className={NAV_LINK_CLASS} data-active={location.pathname === '/architecture'}>
            Architecture
          </NavLink>
        </nav>

        <Link
          to="/catalog"
          className="inline-flex items-center gap-2 rounded-lg border border-border-strong px-3.5 py-2 text-sm font-medium text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          Catalog Search
        </Link>
      </div>
    </header>
  )
}
