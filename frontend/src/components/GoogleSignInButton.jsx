import { useEffect, useRef } from 'react'
import { useSiteSettings } from '../SiteSettingsContext'


/**
 * Botón oficial de "Iniciar sesión con Google" (Google Identity Services).
 * Al elegir una cuenta, Google le entrega al navegador un JWT firmado
 * ("credential"); ese token se manda tal cual al backend, que es quien lo
 * valida de verdad contra los servidores de Google antes de confiar en él.
 */
export default function GoogleSignInButton({ onCredential, text = 'continue_with' }) {
  const buttonRef = useRef(null)
  // Lo entrega el backend (GOOGLE_CLIENT_ID); VITE_GOOGLE_CLIENT_ID queda como respaldo
  const { settings } = useSiteSettings()
  const CLIENT_ID = settings.google_client_id || import.meta.env.VITE_GOOGLE_CLIENT_ID

  useEffect(() => {
    if (!CLIENT_ID) return

    const renderButton = () => {
      if (!window.google || !buttonRef.current) return
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response) => onCredential(response.credential),
      })
      buttonRef.current.innerHTML = ''
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text,
      })
    }

    if (window.google) {
      renderButton()
    } else {
      const interval = setInterval(() => {
        if (window.google) {
          clearInterval(interval)
          renderButton()
        }
      }, 100)
      return () => clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, CLIENT_ID])

  if (!CLIENT_ID) return null

  return <div ref={buttonRef} className="google-btn-wrap" />
}
