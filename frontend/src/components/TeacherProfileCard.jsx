import { useEffect, useState } from 'react'
import { api } from '../api'

const EMPTY = { materia: '', nivel: '', duracion_clase: '', estilo: '', indicaciones: '' }
const NIVELES = ['Pregrado — primeros años', 'Pregrado — años avanzados', 'Posgrado', 'Educación continua']
const ESTILOS = ['Conciso y directo', 'Detallado, con ejemplos', 'Paso a paso', 'Con actividades prácticas']

/** Perfil del docente: el asistente lo usa como contexto en todas sus conversaciones. */
export default function TeacherProfileCard() {
  const [form, setForm] = useState(EMPTY)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.getProfile()
      .then((p) => setForm({ ...EMPTY, ...Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v ?? ''])) }))
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [])

  const set = (k) => (e) => { setStatus(''); setForm((f) => ({ ...f, [k]: e.target.value })) }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true); setError(''); setStatus('')
    try {
      const d = form.duracion_clase === '' ? null : Number(form.duracion_clase)
      const saved = await api.updateProfile({ ...form, duracion_clase: d })
      setForm({ ...EMPTY, ...Object.fromEntries(Object.entries(saved).map(([k, v]) => [k, v ?? ''])) })
      setStatus('Perfil guardado. El asistente lo usará desde tu próximo mensaje.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) return null

  return (
    <form className="profile-card" onSubmit={save}>
      <div className="profile-grid">
        <div className="field">
          <label htmlFor="pf-materia">Materia o área</label>
          <input id="pf-materia" type="text" maxLength={120} placeholder="Ej. Termodinámica" value={form.materia} onChange={set('materia')} />
        </div>
        <div className="field">
          <label htmlFor="pf-nivel">Nivel de tus estudiantes</label>
          <input id="pf-nivel" list="pf-niveles" maxLength={80} placeholder="Elige o escribe" value={form.nivel} onChange={set('nivel')} />
          <datalist id="pf-niveles">{NIVELES.map((n) => <option key={n} value={n} />)}</datalist>
        </div>
        <div className="field">
          <label htmlFor="pf-duracion">Duración de una clase (minutos)</label>
          <input id="pf-duracion" type="number" min={10} max={600} step={5} placeholder="Ej. 90" value={form.duracion_clase} onChange={set('duracion_clase')} />
        </div>
        <div className="field">
          <label htmlFor="pf-estilo">Estilo de respuesta</label>
          <input id="pf-estilo" list="pf-estilos" maxLength={200} placeholder="Elige o escribe" value={form.estilo} onChange={set('estilo')} />
          <datalist id="pf-estilos">{ESTILOS.map((n) => <option key={n} value={n} />)}</datalist>
        </div>
      </div>
      <div className="field">
        <label htmlFor="pf-indicaciones">Otras indicaciones (opcional)</label>
        <textarea id="pf-indicaciones" maxLength={1000} rows={3}
          placeholder="Ej. Mis grupos son de 40 estudiantes; evalúo con rúbricas; prefiero ejemplos de la industria local."
          value={form.indicaciones} onChange={set('indicaciones')} />
      </div>
      {error && <p className="error">{error}</p>}
      <div className="profile-actions">
        <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar perfil'}</button>
        {status && <span className="settings-status">{status}</span>}
      </div>
    </form>
  )
}
