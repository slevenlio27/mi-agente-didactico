import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSiteSettings } from '../SiteSettingsContext'

const KEY = 'agente_didactico_cookie_notice_seen'

export default function CookieBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) setVisible(true)
    } catch {
      setVisible(true)
    }
  }, [])

  const dismiss = () => {
    try { localStorage.setItem(KEY, '1') } catch { /* noop */ }
    setVisible(false)
  }

  const { settings } = useSiteSettings()
  if (!visible || !settings.cookie_banner_enabled) return null

  return (
    <div className="cookie-banner">
      <p>
        Usamos una cookie estrictamente necesaria para mantener tu sesión iniciada, y guardamos tus
        preferencias (tema, materia, IA por defecto) en tu navegador.{' '}
        <Link to="/legal#cookies" onClick={dismiss}>Ver política de cookies</Link>
      </p>
      <button className="btn btn-primary btn-sm" onClick={dismiss}>Entendido</button>
    </div>
  )
}
