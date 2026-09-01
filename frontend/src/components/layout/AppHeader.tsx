import { Menu, X } from 'lucide-react'
import { useEffect, useState, type MouseEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { LogoMark } from '@/components/common/LogoMark'
import { HeaderSearch } from '@/components/layout/HeaderSearch'

const NAV_LINK_CLASS =
  'relative py-1 text-sm font-medium text-muted transition-colors hover:text-foreground ' +
  'data-[active=true]:text-foreground data-[active=true]:after:absolute data-[active=true]:after:inset-x-0 ' +
  'data-[active=true]:after:-bottom-[21px] data-[active=true]:after:h-0.5 ' +
  'data-[active=true]:after:rounded-full data-[active=true]:after:bg-linear-to-r ' +
  'data-[active=true]:after:from-accent data-[active=true]:after:to-accent-2'

const MOBILE_LINK_CLASS =
  'flex items-center justify-between rounded-lg px-4 py-3 text-sm font-semibold text-foreground ' +
  'transition-colors hover:bg-surface-2 data-[active=true]:bg-accent/10 data-[active=true]:text-accent-soft'

export function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  // Route change = navigation happened; the panel's job is done.
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname, location.hash])

  function handleHowItWorksClick(event: MouseEvent<HTMLAnchorElement>) {
    setMenuOpen(false)
    if (location.pathname === '/') {
      event.preventDefault()
      document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else {
      event.preventDefault()
      navigate('/#how-it-works')
    }
  }

  const links = [
    { to: '/catalog', label: 'Catalog' },
    { to: '/architecture', label: 'Architecture' },
  ]

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6 lg:px-10">
        <Link to="/" className="flex items-center gap-2.5" aria-label="PartPilot home">
          <LogoMark />
          <span className="font-display text-[17px] font-bold tracking-tight text-foreground">PartPilot</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          <a href="/#how-it-works" onClick={handleHowItWorksClick} className={NAV_LINK_CLASS}>
            How It Works
          </a>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={NAV_LINK_CLASS}
              data-active={location.pathname === link.to}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <HeaderSearch className="hidden w-56 sm:block lg:w-72" />
          <button
            type="button"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-border-strong text-foreground transition-colors hover:border-accent/50 md:hidden"
          >
            {menuOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav
          aria-label="Primary, mobile"
          className="animate-fade-in border-t border-border bg-background/98 px-4 pt-3 pb-4 backdrop-blur md:hidden"
        >
          <HeaderSearch className="mb-3 sm:hidden" onNavigate={() => setMenuOpen(false)} />
          <a href="/#how-it-works" onClick={handleHowItWorksClick} className={MOBILE_LINK_CLASS}>
            How It Works
          </a>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={MOBILE_LINK_CLASS}
              data-active={location.pathname === link.to}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
