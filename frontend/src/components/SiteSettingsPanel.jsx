import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { applySiteAppearance, DEFAULT_SETTINGS, useSiteSettings } from '../SiteSettingsContext'

const CHAT_DEFAULTS = { anthropic: '#c2603a', openai: '#1f9a82', gemini: '#5b5bd6' }

const FEATURE_GROUPS = [
  {
    title: 'Cuentas',
    items: [
      ['registration_enabled', 'Registro de cuentas nuevas', 'Si lo apagas, solo las cuentas existentes pueden entrar.'],
      ['google_login_enabled', 'Iniciar sesión con Google', 'Los administradores conservan este acceso aunque lo apagues.'],
    ],
  },
  {
    title: 'Funciones',
    items: [
      ['chat_enabled', 'Asistente de IA', 'Oculta el chat flotante y bloquea nuevas consultas.'],
      ['uploads_enabled', 'Subida de archivos', 'Los docentes siguen pudiendo ver y borrar lo que ya subieron.'],
      ['agenda_enabled', 'Agenda semanal', 'Oculta la agenda del panel docente.'],
      ['own_api_keys_enabled', 'Claves de API propias', 'Si lo apagas, todas las consultas usan las claves del servidor.'],
    ],
  },
  {
    title: 'Proveedores de IA',
    items: [
      ['provider_anthropic_enabled', 'Claude (Anthropic)', ''],
      ['provider_openai_enabled', 'ChatGPT (OpenAI)', ''],
      ['provider_gemini_enabled', 'Gemini (Google)', ''],
    ],
  },
  {
    title: 'Privacidad',
    items: [
      ['analytics_enabled', 'Estadísticas de visitas', 'Registro anónimo de páginas visitadas (sin IP).'],
      ['cookie_banner_enabled', 'Aviso de cookies', 'Revisa la normativa de tu país antes de apagarlo.'],
      ['materia_colors_enabled', 'Colores por materia', 'Si lo apagas, todos ven solo el color institucional.'],
    ],
  },
]

function Toggle({ id, label, desc, checked, onChange }) {
  return (
    <label className="toggle-row" htmlFor={id}>
      <div>
        <div className="t-label">{label}</div>
        {desc && <div className="t-desc">{desc}</div>}
      </div>
      <span className="switch">
        <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="slider" />
      </span>
    </label>
  )
}

function ColorRow({ id, label, value, fallback, onChange, onReset }) {
  return (
    <div className="color-row">
      <label htmlFor={id}>{label}</label>
      <span className="color-meta">{value || 'por defecto'}</span>
      {onReset && value && (
        <button type="button" className="reset-btn" onClick={onReset}>Restablecer</button>
      )}
      <input id={id} type="color" value={value || fallback} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

export default function SiteSettingsPanel() {
  const { settings: saved, refresh } = useSiteSettings()
  const [draft, setDraft] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    api.adminGetSettings()
      .then((s) => setDraft({ ...DEFAULT_SETTINGS, ...s }))
      .catch((e) => setError(e.message))
  }, [])

  // Vista previa en vivo de colores y nombre mientras se edita. Al salir del
  // panel sin guardar, se vuelve a aplicar la configuración guardada.
  const savedRef = useRef(saved)
  savedRef.current = saved
  useEffect(() => { if (draft) applySiteAppearance(draft) }, [draft])
  useEffect(() => () => applySiteAppearance(savedRef.current), [])

  if (!draft) return error ? <p className="error">{error}</p> : <p className="empty-hint">Cargando configuración…</p>

  const set = (key, value) => { setStatus(''); setDraft((d) => ({ ...d, [key]: value })) }
  const dirty = JSON.stringify(draft) !== JSON.stringify({ ...DEFAULT_SETTINGS, ...saved })

  const handleSave = async () => {
    setSaving(true); setError(''); setStatus('')
    try {
      const payload = { ...draft }
      for (const p of ['anthropic', 'openai', 'gemini']) {
        payload[`chat_color_${p}`] = draft[`chat_color_${p}`] || ''  // "" = color por defecto
      }
      const updated = await api.adminUpdateSettings(payload)
      setDraft({ ...DEFAULT_SETTINGS, ...updated })
      await refresh()
      setStatus('Cambios guardados y aplicados a todo el sitio.')
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDiscard = () => { setDraft({ ...DEFAULT_SETTINGS, ...saved }); setError(''); setStatus('') }

  return (
    <>
      {error && <p className="error">{error}</p>}
      <div className="settings-grid">
        <div className="settings-card">
          <h3>Apariencia</h3>
          <p className="hint">Los cambios se ven en vivo mientras editas; se aplican a todos al guardar.</p>

          <div className="field">
            <label htmlFor="set-name">Nombre del sitio</label>
            <input id="set-name" type="text" maxLength={60} value={draft.site_name}
              onChange={(e) => set('site_name', e.target.value)} />
          </div>

          <div className="settings-group-title">Color institucional</div>
          <ColorRow id="c-light" label="Modo claro" value={draft.accent_light} fallback="#1f8a73"
            onChange={(v) => set('accent_light', v)} />
          <ColorRow id="c-dark" label="Modo oscuro" value={draft.accent_dark} fallback="#5fcdb1"
            onChange={(v) => set('accent_dark', v)} />
          <div style={{ marginTop: 10 }}><span className="preview-chip">Vista previa del botón</span></div>

          <div className="settings-group-title">Color del chat según la IA</div>
          {['anthropic', 'openai', 'gemini'].map((p) => (
            <ColorRow key={p} id={`c-${p}`}
              label={{ anthropic: 'Claude', openai: 'ChatGPT', gemini: 'Gemini' }[p]}
              value={draft[`chat_color_${p}`]} fallback={CHAT_DEFAULTS[p]}
              onChange={(v) => set(`chat_color_${p}`, v)}
              onReset={() => set(`chat_color_${p}`, null)} />
          ))}
        </div>

        <div className="settings-card">
          <h3>Funciones del sitio</h3>
          <p className="hint">Se bloquean también en el servidor, no solo se ocultan.</p>
          {FEATURE_GROUPS.map((g) => (
            <div key={g.title}>
              <div className="settings-group-title">{g.title}</div>
              {g.items.map(([key, label, desc]) => (
                <Toggle key={key} id={`t-${key}`} label={label} desc={desc}
                  checked={!!draft[key]} onChange={(v) => set(key, v)} />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="settings-actions">
        <button className="btn btn-primary" onClick={handleSave} disabled={saving || !dirty}>
          {saving ? 'Guardando…' : 'Guardar cambios'}
        </button>
        <button className="btn btn-ghost" onClick={handleDiscard} disabled={saving || !dirty}>Descartar</button>
        {status && <span className="settings-status">{status}</span>}
      </div>
    </>
  )
}
