import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import { useChatWidget } from '../ChatWidgetContext'
import { useSiteSettings } from '../SiteSettingsContext'
import TeacherProfileCard from '../components/TeacherProfileCard'

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

const PROVIDER_LABELS = { anthropic: 'Claude', openai: 'ChatGPT', gemini: 'Gemini' }
const DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const DAY_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function weekDates() {
  const now = new Date()
  const dow = (now.getDay() + 6) % 7 // 0 = lunes
  const monday = new Date(now)
  monday.setDate(now.getDate() - dow)
  const out = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    out.push({ label: DAY_SHORT[i], date: `${d.getDate()}/${d.getMonth() + 1}` })
  }
  return out
}

export default function Dashboard() {
  const { user } = useAuth()
  const { openWidget, refreshSignal } = useChatWidget()
  const { settings } = useSiteSettings()

  const [sessions, setSessions] = useState([])
  const [files, setFiles] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [selectedDay, setSelectedDay] = useState((new Date().getDay() + 6) % 7)
  const [evTitle, setEvTitle] = useState('')
  const [evStart, setEvStart] = useState('08:00')
  const [evEnd, setEvEnd] = useState('09:30')

  const dates = weekDates()

  const loadAll = async () => {
    try {
      const [s, f, e] = await Promise.all([api.listSessions(), api.listFiles(), api.listEvents()])
      setSessions(s)
      setFiles(f)
      setEvents(e)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [refreshSignal])

  useEffect(() => {
    if (window.location.hash === '#historial') {
      document.getElementById('historial')?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation()
    await api.deleteSession(id)
    loadAll()
  }

  const handleUploadFiles = async (fileList) => {
    setError('')
    for (const file of Array.from(fileList)) {
      try {
        await api.uploadFile(file, null)
      } catch (err) {
        setError(err.message)
      }
    }
    loadAll()
  }

  const handleDeleteFile = async (id) => {
    await api.deleteFile(id)
    loadAll()
  }

  const handleAddEvent = async (e) => {
    e.preventDefault()
    if (!evTitle.trim()) return
    setError('')
    try {
      await api.createEvent({ day_of_week: selectedDay, title: evTitle.trim(), start_time: evStart, end_time: evEnd })
      setEvTitle('')
      loadAll()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteEvent = async (id) => {
    await api.deleteEvent(id)
    loadAll()
  }

  const sessionsThisWeek = sessions.filter((s) => {
    const created = new Date(s.created_at)
    return Date.now() - created.getTime() < 7 * 24 * 60 * 60 * 1000
  }).length

  if (loading) return <div className="center-msg">Cargando panel…</div>

  return (
    <>
      <section className="panel-hero page-section" style={{ paddingBottom: 20 }}>
        <div className="wrap">
          <div className="eyebrow">Tu panel</div>
          <h1>Hola, {user?.full_name?.split(' ')[0] || user?.email}.</h1>
          {error && <p className="error">{error}</p>}
          <div className="panel-stats">
            <div className="stat"><strong>{sessions.length}</strong><span>Temas trabajados</span></div>
            <div className="stat"><strong>{sessionsThisWeek}</strong><span>Conversaciones esta semana</span></div>
            <div className="stat"><strong>{files.length}</strong><span>Documentos</span></div>
          </div>
        </div>
      </section>

      <section id="perfil" className="page-section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Tu perfil docente</div>
            <h2>Cuéntale al asistente cómo enseñas</h2>
            <p>Se usa como contexto en todas tus conversaciones, para que las respuestas salgan adaptadas a tu materia y a tus clases sin repetirlo cada vez.</p>
          </div>
          <TeacherProfileCard />
        </div>
      </section>

      <section id="historial" className="page-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Historial</div>
            <h2>Tus últimas conversaciones</h2>
            <p>Elige una para retomarla en el asistente, en la esquina inferior derecha.</p>
          </div>
          <div className="topic-list">
            {sessions.map((s) => {
              const docCount = files.filter((f) => f.session_id === s.id).length
              return (
                <div key={s.id} className="topic-row" onClick={() => openWidget(s.id)}>
                  <span className="topic-dot"></span>
                  <div className="topic-main">
                    <div className="topic-materia">{PROVIDER_LABELS[s.provider] || s.provider}</div>
                    <div className="topic-title">{s.title}</div>
                    <div className="topic-meta">{docCount} documento{docCount === 1 ? '' : 's'}</div>
                  </div>
                  <span className="topic-date">{formatDate(s.updated_at)}</span>
                  <button className="topic-del" aria-label="Eliminar" onClick={(e) => handleDeleteSession(e, s.id)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>
                  </button>
                </div>
              )
            })}
            {sessions.length === 0 && <p className="empty-hint">Todavía no tienes conversaciones. Abre el asistente para empezar una.</p>}
          </div>
        </div>
      </section>

      {settings.agenda_enabled && (
      <section id="agenda" className="page-section alt-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Fechas y horarios</div>
            <h2>Agenda</h2>
            <p>Tu semana de un vistazo. Selecciona un día o añade un evento.</p>
          </div>
          <div className="agenda-grid">
            <div className="day-tabs" role="tablist" aria-label="Días de la semana">
              {dates.map((d, i) => {
                const count = events.filter((e) => e.day_of_week === i).length
                return (
                  <button
                    key={i}
                    className={`day-tab ${selectedDay === i ? 'active' : ''}`}
                    role="tab"
                    aria-selected={selectedDay === i}
                    onClick={() => setSelectedDay(i)}
                  >
                    <span className="d-name">{d.label}</span>
                    <span className="d-date">{d.date}</span>
                    <span className="d-count">{count}</span>
                  </button>
                )
              })}
            </div>
            <div className="agenda-panel">
              <div className="agenda-day-title">{DAY_NAMES[selectedDay]} · {dates[selectedDay].date}</div>
              <div className="slot-list">
                {events.filter((e) => e.day_of_week === selectedDay).length === 0 && (
                  <p className="empty-day">Sin eventos para este día. Añade uno con el formulario.</p>
                )}
                {events.filter((e) => e.day_of_week === selectedDay).map((e) => (
                  <div key={e.id} className="slot">
                    <div className="slot-time">{e.start_time} – {e.end_time}</div>
                    <div className="slot-title">{e.title}</div>
                    <button className="slot-del" aria-label="Eliminar evento" onClick={() => handleDeleteEvent(e.id)}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>
                    </button>
                  </div>
                ))}
              </div>
              <form className="add-event" onSubmit={handleAddEvent}>
                <div className="field" style={{ flex: 2 }}>
                  <label htmlFor="ev-title">Título</label>
                  <input id="ev-title" type="text" placeholder="Ej. Clase — Física" required value={evTitle} onChange={(e) => setEvTitle(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="ev-start">Inicio</label>
                  <input id="ev-start" type="time" required value={evStart} onChange={(e) => setEvStart(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="ev-end">Fin</label>
                  <input id="ev-end" type="time" required value={evEnd} onChange={(e) => setEvEnd(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary btn-sm">Añadir</button>
              </form>
            </div>
          </div>
        </div>
      </section>
      )}

      <section id="galeria" className="page-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Galería</div>
            <h2>Documentos que has subido</h2>
          </div>
          {settings.uploads_enabled && (
          <div
            className={`dropzone ${dragOver ? 'drag' : ''}`}
            tabIndex={0}
            role="button"
            aria-label="Subir archivos"
            onClick={() => document.getElementById('dash-file-input').click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUploadFiles(e.dataTransfer.files) }}
          >
            <strong>Arrastra archivos aquí, o haz clic para elegir</strong>
            <p>PDF, imágenes (PNG, JPEG, WEBP) o texto (TXT, Markdown)</p>
            <input
              id="dash-file-input"
              type="file"
              multiple
              accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
              hidden
              onChange={(e) => handleUploadFiles(e.target.files)}
            />
          </div>
          )}

          <div className="gallery-grid">
            {files.map((f) => (
              <div key={f.id} className="file-card">
                {f.content_type.startsWith('image/') ? (
                  <img src={api.fileDownloadUrl(f.id)} alt={f.original_name} />
                ) : (
                  <div className="file-icon">📄</div>
                )}
                <p className="file-name" title={f.original_name}>{f.original_name}</p>
                <p className="file-meta">{(f.size_bytes / 1024).toFixed(0)} KB</p>
                <div className="file-actions">
                  <a href={api.fileDownloadUrl(f.id)} target="_blank" rel="noreferrer">Ver / descargar</a>
                  <button onClick={() => handleDeleteFile(f.id)}>Eliminar</button>
                </div>
              </div>
            ))}
            {files.length === 0 && <p className="empty-hint">Aún no has subido archivos.</p>}
          </div>
        </div>
      </section>
    </>
  )
}
