import { useEffect, useState } from 'react'
import { useAuth } from '../AuthContext'
import { api } from '../api'
import { useAuthModal } from '../AuthModalContext'
import GoogleSignInButton from './GoogleSignInButton'
import { useSiteSettings } from '../SiteSettingsContext'

export default function AuthModal() {
  const { isOpen, close } = useAuthModal()
  const { login, register, loginWithGoogle } = useAuth()

  const { settings } = useSiteSettings()
  const [modeState, setMode] = useState('login') // 'login' | 'register' | 'forgot'
  // Si el admin apagó el registro, el modal solo ofrece iniciar sesión.
  // El registro puede estar desactivado; recuperar la contraseña, siempre está disponible
  const mode = modeState === 'register' && !settings.registration_enabled ? 'login' : modeState
  const [forgotDone, setForgotDone] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Cada vez que se abre, empieza en «Inicia sesión»
  useEffect(() => { if (isOpen) { setMode('login'); setForgotDone(''); setError('') } }, [isOpen])

  if (!isOpen) return null

  const reset = () => {
    setError('')
    setPassword('')
  }

  const handleGoogle = async (credential) => {
    setError('')
    try {
      await loginWithGoogle(credential)
      close()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'forgot') {
        const r = await api.requestPasswordReset(email)
        setForgotDone(r.detail)
        return
      }
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password, fullName)
      }
      close()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="modal-overlay open"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-title"
      onClick={(e) => e.target === e.currentTarget && close()}
    >
      <div className="modal-box">
        <div className="modal-head">
          <h3 id="login-title">{mode === 'login' ? 'Inicia sesión' : mode === 'register' ? 'Crea tu cuenta' : 'Recuperar contraseña'}</h3>
          <button aria-label="Cerrar" onClick={close}>✕</button>
        </div>
        <div className="modal-body">
          <p className="hint">
            {mode === 'login'
              ? 'Entra con Google o con tu correo para que el sitio recuerde tu historial y tus preferencias de IA.'
              : mode === 'register'
                ? 'Crea una cuenta con Google o con correo y contraseña.'
                : 'Escribe el correo de tu cuenta. El administrador recibirá tu solicitud y te enviará un enlace para elegir una contraseña nueva.'}
          </p>

          {/* Solo si Google está activo en el sitio Y configurado (Client ID); si no, no habría botón y el separador quedaría huérfano */}
          {mode !== 'forgot' && settings.google_login_enabled && (settings.google_client_id || import.meta.env.VITE_GOOGLE_CLIENT_ID) && (
            <>
              <GoogleSignInButton onCredential={handleGoogle} text={mode === 'login' ? 'signin_with' : 'signup_with'} />
              <div className="oauth-divider"><span>o con tu correo</span></div>
            </>
          )}

          {error && <p className="error">{error}</p>}

          {mode === 'forgot' && forgotDone ? (
            <div className="forgot-done" role="status">
              <p>{forgotDone}</p>
              <p className="hint">Si te registraste con Google, no necesitas contraseña: entra con el botón de Google.</p>
              <button type="button" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => { setMode('login'); setForgotDone('') }}>
                Volver a iniciar sesión
              </button>
            </div>
          ) : (
          <form onSubmit={handleSubmit}>
            {mode === 'register' && (
              <div className="field">
                <label htmlFor="auth-name">Nombre completo</label>
                <input
                  id="auth-name"
                  type="text"
                  placeholder="Prof. Ana Martínez"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            )}
            <div className="field">
              <label htmlFor="auth-email">Correo</label>
              <input
                id="auth-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {mode !== 'forgot' && (
            <div className="field">
              <div className="label-row">
                <label htmlFor="auth-password">Contraseña</label>
                {mode === 'login' && (
                  <button type="button" className="link-btn forgot-link" onClick={() => { setMode('forgot'); reset() }}>
                    ¿Olvidaste tu contraseña?
                  </button>
                )}
              </div>
              <input
                id="auth-password"
                type="password"
                required
                minLength={mode === 'register' ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            )}
            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
              {loading ? 'Un momento…' : mode === 'login' ? 'Entrar' : mode === 'register' ? 'Crear cuenta' : 'Enviar solicitud'}
            </button>
          </form>
          )}

          {mode === 'forgot' && !forgotDone && (
            <p className="hint" style={{ marginTop: 14, textAlign: 'center' }}>
              <button type="button" className="link-btn" style={{ color: 'var(--accent)', textDecoration: 'underline' }} onClick={() => { setMode('login'); reset() }}>Volver a iniciar sesión</button>
            </p>
          )}
          {mode !== 'forgot' && settings.registration_enabled && (
          <p className="hint" style={{ marginTop: 14, textAlign: 'center' }}>
            {mode === 'login' ? (
              <>¿No tienes cuenta?{' '}
                <button type="button" className="link-btn" style={{ color: 'var(--accent)', textDecoration: 'underline' }} onClick={() => { setMode('register'); reset() }}>Regístrate</button>
              </>
            ) : (
              <>¿Ya tienes cuenta?{' '}
                <button type="button" className="link-btn" style={{ color: 'var(--accent)', textDecoration: 'underline' }} onClick={() => { setMode('login'); reset() }}>Inicia sesión</button>
              </>
            )}
          </p>
          )}
        </div>
      </div>
    </div>
  )
}
