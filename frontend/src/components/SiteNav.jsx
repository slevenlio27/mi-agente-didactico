import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useAuthModal } from '../AuthModalContext'
import { useTheme } from '../ThemeContext'
import { useSiteSettings } from '../SiteSettingsContext'
import PreferencesModal from './PreferencesModal'

const SUN = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/></svg>
const MOON = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z"/></svg>

function initials(name) {
  if (!name) return 'P'
  return name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase() || 'P'
}

export default function SiteNav({ onOpenDrawer }) {
  const { user, logout } = useAuth()
  const { open: openAuthModal } = useAuthModal()
  const { dark, toggleDark } = useTheme()
  const { settings } = useSiteSettings()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [prefsOpen, setPrefsOpen] = useState(false)

  const displayName = user?.full_name || user?.email || ''

  return (
    <>
      <header className="site-nav">
        <div className="nav-inner">
          <Link to="/" className="brand">
            <span className="stamp-mark"><span>IA</span></span>{settings.site_name}
          </Link>
          <nav className="links" aria-label="Secciones">
            <a href="/#beneficios">Beneficios</a>
            <a href="/#que-hace">Qué puede hacer</a>
            <a href="/#como-funciona">Cómo funciona</a>
            {user && <Link to="/panel">Panel docente</Link>}
            {user?.is_admin && <Link to="/admin">Administración</Link>}
          </nav>
          <div className="nav-actions">
            <button className="mode-toggle" aria-pressed={dark} onClick={toggleDark} aria-label={dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}>
              <span>{dark ? SUN : MOON}</span>
              <span id="mode-label">{dark ? 'Modo claro' : 'Modo oscuro'}</span>
            </button>

            {!user ? (
              <button className="btn btn-primary btn-sm" onClick={openAuthModal}>Iniciar sesión</button>
            ) : (
              <div className="account-wrap">
                <button
                  className="account-pill"
                  aria-expanded={menuOpen}
                  aria-haspopup="true"
                  onClick={() => setMenuOpen((o) => !o)}
                >
                  <span className="avatar">{initials(displayName)}</span>
                  <span>{displayName.split(' ')[0]}</span>
                </button>
                {menuOpen && (
                  <div className="account-menu open" onMouseLeave={() => setMenuOpen(false)}>
                    <button onClick={() => { setMenuOpen(false); setPrefsOpen(true) }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"></path></svg>
                      Preferencias de IA
                    </button>
                    <button onClick={() => { setMenuOpen(false); navigate('/panel#historial') }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"><path d="M3 6a1 1 0 0 1 1-1h4l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6Z"></path></svg>
                      Mi historial
                    </button>
                    {user.is_admin && (
                      <button onClick={() => { setMenuOpen(false); navigate('/admin') }}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"><path d="M12 3 4 7v5c0 4.2 3 7.6 8 9 5-1.4 8-4.8 8-9V7l-8-4Z"></path></svg>
                        Administración
                      </button>
                    )}
                    <div className="divider" />
                    <button onClick={() => { setMenuOpen(false); logout() }}>Cerrar sesión</button>
                  </div>
                )}
              </div>
            )}

            <button className="menu-btn" aria-label="Abrir menú" onClick={onOpenDrawer}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h16"></path></svg>
            </button>
          </div>
        </div>
      </header>
      <PreferencesModal open={prefsOpen} onClose={() => setPrefsOpen(false)} />
    </>
  )
}
