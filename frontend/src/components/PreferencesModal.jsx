import { useEffect, useState } from 'react'
import { api } from '../api'
import { enabledProviders, useSiteSettings } from '../SiteSettingsContext'

const PROVIDER_KEY = 'agente_didactico_default_provider'
const PROVIDERS = [
  { id: 'anthropic', title: 'Claude', desc: 'Listo para usar con la clave del servidor. Analiza PDF, imágenes y texto.', field: 'anthropic_api_key', statusField: 'has_anthropic_key' },
  { id: 'openai', title: 'ChatGPT (OpenAI)', desc: 'Admite texto e imágenes.', field: 'openai_api_key', statusField: 'has_openai_key' },
  { id: 'gemini', title: 'Google Gemini', desc: 'Admite texto, imágenes y PDF.', field: 'gemini_api_key', statusField: 'has_gemini_key' },
]

/** IA por defecto del docente; si el admin la desactivó, usa la primera activa. */
export function getDefaultProvider(enabled = ['anthropic', 'openai', 'gemini']) {
  let stored = null
  try { stored = localStorage.getItem(PROVIDER_KEY) } catch { /* noop */ }
  if (stored && enabled.includes(stored)) return stored
  return enabled[0] || 'anthropic'
}

export default function PreferencesModal({ open, onClose }) {
  const { settings } = useSiteSettings()
  const enabled = enabledProviders(settings)
  const visibleProviders = PROVIDERS.filter((p) => enabled.includes(p.id))
  const ownKeys = settings.own_api_keys_enabled
  const [selected, setSelected] = useState(getDefaultProvider(enabled))
  const [keyStatus, setKeyStatus] = useState({})
  const [keyInputs, setKeyInputs] = useState({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [savedMsg, setSavedMsg] = useState('')

  useEffect(() => {
    if (!open) return
    setSelected(getDefaultProvider(enabled))
    setKeyInputs({})
    setError('')
    setSavedMsg('')
    api.getApiKeysStatus().then(setKeyStatus).catch(() => {})
  }, [open])

  if (!open) return null

  const handleSaveDefault = () => {
    try {
      localStorage.setItem(PROVIDER_KEY, selected)
    } catch {
      /* si el navegador bloquea localStorage, la preferencia solo dura esta sesión */
    }
  }

  const handleSaveKeys = async () => {
    setSaving(true)
    setError('')
    setSavedMsg('')
    handleSaveDefault()
    // Solo mandamos los campos que el docente realmente tocó, para no
    // borrar por accidente una clave ya guardada que dejó en blanco.
    const payload = {}
    for (const p of PROVIDERS) {
      if (keyInputs[p.field] !== undefined) payload[p.field] = keyInputs[p.field]
    }
    try {
      if (Object.keys(payload).length > 0) {
        const status = await api.updateApiKeys(payload)
        setKeyStatus(status)
      }
      setKeyInputs({})
      setSavedMsg('Preferencias guardadas.')
      setTimeout(onClose, 700)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleClearKey = (field) => {
    setKeyInputs((prev) => ({ ...prev, [field]: '' }))
  }

  return (
    <div className="modal-overlay open" role="dialog" aria-modal="true" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-head">
          <h3>Preferencias de IA</h3>
          <button aria-label="Cerrar" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <p className="hint">
            Elige tu IA por defecto para conversaciones nuevas.
            {ownKeys && ' Si además pegas tu propia clave de API para un proveedor, tus conversaciones con esa IA se facturan a tu propia cuenta — no a la del servidor. Tu clave se guarda cifrada en el servidor y nunca se vuelve a mostrar en pantalla; las claves de Gemini se comprueban con Google antes de guardarlas.'}
          </p>

          {error && <p className="error">{error}</p>}
          {savedMsg && <p className="hint" style={{ color: 'var(--accent-ink)' }}>{savedMsg}</p>}

          <div className="provider-options">
            {visibleProviders.map((p) => (
              <label key={p.id} className={`provider-card ${selected === p.id ? 'active' : ''}`}>
                <input
                  type="radio"
                  name="provider"
                  value={p.id}
                  checked={selected === p.id}
                  onChange={() => setSelected(p.id)}
                />
                <div style={{ flex: 1 }}>
                  <div className="pc-title">{p.title}</div>
                  <div className="pc-desc">{p.desc}</div>
                  {!ownKeys && keyStatus[p.statusField] && (
                    <div className="pc-desc" style={{ marginTop: 8 }}>
                      Tienes una clave guardada que ya no se usa (el administrador desactivó las claves propias).{' '}
                      <button type="button" className="link-btn" style={{ color: 'var(--accent-ink)', textDecoration: 'underline' }}
                        onClick={(e) => { e.stopPropagation(); handleClearKey(p.field) }}>
                        {keyInputs[p.field] === '' ? 'Se quitará al guardar' : 'Quitarla'}
                      </button>
                    </div>
                  )}
                  {ownKeys && (
                  <div className="field" style={{ marginTop: 10, marginBottom: 0 }}>
                    <label htmlFor={`key-${p.id}`}>
                      Tu clave de API {keyStatus[p.statusField] ? '(ya configurada)' : '(opcional)'}
                    </label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        id={`key-${p.id}`}
                        type="password"
                        placeholder={keyStatus[p.statusField] ? '•••••••••••• (déjalo en blanco para conservarla)' : 'sk-...'}
                        value={keyInputs[p.field] ?? ''}
                        onChange={(e) => setKeyInputs((prev) => ({ ...prev, [p.field]: e.target.value }))}
                        onClick={(e) => e.stopPropagation()}
                      />
                      {keyStatus[p.statusField] && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={(e) => { e.stopPropagation(); handleClearKey(p.field) }}
                        >
                          Quitar
                        </button>
                      )}
                    </div>
                  </div>
                  )}
                </div>
              </label>
            ))}
          </div>

          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 18 }} onClick={handleSaveKeys} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar preferencias'}
          </button>
        </div>
      </div>
    </div>
  )
}
