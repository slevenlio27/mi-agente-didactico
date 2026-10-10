import { useState } from 'react'
import { api } from '../api'

// Dónde crea cada docente su propia clave, según la IA de la conversación.
const PROVIDERS = {
  gemini: { name: 'Gemini', field: 'gemini_api_key', url: 'https://aistudio.google.com/apikey', site: 'Google AI Studio', placeholder: 'AIza…' },
  openai: { name: 'ChatGPT', field: 'openai_api_key', url: 'https://platform.openai.com/api-keys', site: 'la plataforma de OpenAI', placeholder: 'sk-…' },
  anthropic: { name: 'Claude', field: 'anthropic_api_key', url: 'https://console.anthropic.com/settings/keys', site: 'la consola de Anthropic', placeholder: 'sk-ant-…' },
}

/**
 * Aviso guiado dentro del chat cuando el docente no tiene clave para la IA de la
 * conversación (o la que tenía dejó de funcionar). Permite pegar la clave ahí mismo.
 */
export default function KeySetupCard({ provider, ownKeysAllowed, invalid, onSaved }) {
  const p = PROVIDERS[provider] || PROVIDERS.gemini
  const [key, setKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!ownKeysAllowed) {
    return (
      <div className="key-card" role="status">
        <strong>El asistente aún no está configurado</strong>
        <p>Pide a quien administra el sitio que agregue una clave de {p.name} en el servidor.</p>
      </div>
    )
  }

  const save = async (e) => {
    e.preventDefault()
    if (!key.trim()) return
    setSaving(true); setError('')
    try {
      await api.updateApiKeys({ [p.field]: key.trim() })
      setKey('')
      onSaved?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="key-card" role="region" aria-label={`Conectar tu clave de ${p.name}`}>
      <strong>{invalid ? `Tu clave de ${p.name} dejó de funcionar` : `Conecta tu cuenta de ${p.name}`}</strong>
      <p>
        {invalid
          ? 'Google la rechazó. Crea una nueva y pégala aquí para seguir conversando.'
          : `Para usar el asistente necesitas tu propia clave de ${p.name}. Tus consultas usarán la cuota de tu cuenta, no la del sitio.`}
      </p>
      <ol className="key-steps">
        <li>
          <a className="btn btn-primary btn-sm" href={p.url} target="_blank" rel="noopener noreferrer">
            Crear mi clave en {p.site} ↗
          </a>
        </li>
        <li>
          <form onSubmit={save} className="key-form">
            <label htmlFor="key-setup-input">Pega tu clave aquí</label>
            <div className="key-row">
              <input id="key-setup-input" type="password" autoComplete="off" spellCheck="false"
                placeholder={p.placeholder} value={key} onChange={(e) => setKey(e.target.value)} />
              <button type="submit" className="btn btn-primary btn-sm" disabled={saving || !key.trim()}>
                {saving ? 'Comprobando…' : 'Guardar'}
              </button>
            </div>
          </form>
        </li>
      </ol>
      {error && <p className="key-error">{error}</p>}
      <p className="key-note">
        {provider === 'gemini' && 'Antes de guardarla comprobamos con Google que funciona. '}
        Se guarda cifrada en el servidor y no vuelve a mostrarse.
        {provider === 'gemini' && ' En el nivel gratuito, Google puede usar el contenido de las consultas para mejorar sus productos.'}
      </p>
    </div>
  )
}
