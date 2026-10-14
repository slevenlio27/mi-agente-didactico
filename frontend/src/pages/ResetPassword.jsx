import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuthModal } from '../AuthModalContext'

/**
 * Página del enlace para elegir una contraseña nueva: /restablecer#token=…
 * El código va después del "#", así que nunca llega al servidor ni queda en sus registros.
 */
export default function ResetPassword() {
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || '')
  const [estado, setEstado] = useState('comprobando') // comprobando | invalido | formulario | listo
  const [pista, setPista] = useState('')
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const navigate = useNavigate()
  const { open } = useAuthModal()

  useEffect(() => {
    // Quita el código de la barra de direcciones (y del historial del navegador)
    if (window.location.hash) window.history.replaceState(null, '', window.location.pathname)
    if (!token) { setEstado('invalido'); return }
    api.validateResetToken(token)
      .then((r) => { if (r.valid) { setPista(r.email_hint); setEstado('formulario') } else setEstado('invalido') })
      .catch(() => setEstado('invalido'))
  }, [token])

  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    if (pw.length < 8) return setError('La contraseña debe tener al menos 8 caracteres.')
    if (pw !== pw2) return setError('Las dos contraseñas no coinciden.')
    setEnviando(true)
    try {
      await api.confirmPasswordReset(token, pw)
      setEstado('listo')
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  const irAIniciarSesion = () => { navigate('/'); open() }

  return (
    <section className="page-section reset-page">
      <div className="wrap">
        <div className="reset-card">
          {estado === 'comprobando' && <p className="hint">Comprobando el enlace…</p>}

          {estado === 'invalido' && (
            <>
              <div className="eyebrow">Restablecer contraseña</div>
              <h2>Este enlace no es válido</h2>
              <p className="hint">Puede que ya se haya usado, que haya vencido (dura 24 horas) o que esté incompleto. Pide uno nuevo desde «¿Olvidaste tu contraseña?» o al administrador de la plataforma.</p>
              <button className="btn btn-primary" onClick={irAIniciarSesion}>Ir a iniciar sesión</button>
            </>
          )}

          {estado === 'formulario' && (
            <>
              <div className="eyebrow">Restablecer contraseña</div>
              <h2>Elige tu nueva contraseña</h2>
              <p className="hint">Para la cuenta <strong>{pista}</strong>. Usa al menos 8 caracteres.</p>
              {error && <p className="error">{error}</p>}
              <form onSubmit={guardar}>
                <div className="field">
                  <label htmlFor="new-pw">Nueva contraseña</label>
                  <input id="new-pw" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={pw} onChange={(e) => setPw(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="new-pw2">Repite la contraseña</label>
                  <input id="new-pw2" type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={pw2} onChange={(e) => setPw2(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={enviando}>
                  {enviando ? 'Guardando…' : 'Guardar contraseña'}
                </button>
              </form>
            </>
          )}

          {estado === 'listo' && (
            <>
              <div className="eyebrow">Restablecer contraseña</div>
              <h2>¡Listo! Tu contraseña se actualizó</h2>
              <p className="hint">Ya puedes iniciar sesión con tu nueva contraseña. El enlace dejó de funcionar.</p>
              <button className="btn btn-primary" onClick={irAIniciarSesion}>Iniciar sesión</button>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
