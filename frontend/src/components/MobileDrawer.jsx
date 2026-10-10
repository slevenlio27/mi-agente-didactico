import { Link } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useAuthModal } from '../AuthModalContext'
import { useChatWidget } from '../ChatWidgetContext'
import { useSiteSettings } from '../SiteSettingsContext'

export default function MobileDrawer({ open, onClose }) {
  const { user } = useAuth()
  const { open: openAuthModal } = useAuthModal()
  const { openWidget } = useChatWidget()
  const { settings } = useSiteSettings()

  return (
    <div id="mobile-drawer" className={open ? 'open' : ''} onClick={(e) => e.target.id === 'mobile-drawer' && onClose()}>
      <div className="drawer-panel">
        <button id="drawer-close" aria-label="Cerrar menú" onClick={onClose}>✕</button>
        <nav>
          <a href="/#beneficios" onClick={onClose}>Beneficios</a>
          <a href="/#que-hace" onClick={onClose}>Qué puede hacer</a>
          <a href="/#como-funciona" onClick={onClose}>Cómo funciona</a>
          {user && <Link to="/panel" onClick={onClose}>Panel docente</Link>}
          {user?.is_admin && <Link to="/admin" onClick={onClose}>Administración</Link>}
        </nav>
        {settings.chat_enabled && (
          <button
            className="btn btn-primary"
            style={{ justifyContent: 'center' }}
            onClick={() => { onClose(); openWidget() }}
          >
            Abrir asistente
          </button>
        )}
        {!user && (
          <button className="btn btn-ghost" style={{ justifyContent: 'center' }} onClick={() => { onClose(); openAuthModal() }}>
            Iniciar sesión
          </button>
        )}
      </div>
    </div>
  )
}
