import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import BarChart from '../components/BarChart'
import SiteSettingsPanel from '../components/SiteSettingsPanel'

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

export default function Admin() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setError('')
    try {
      const [s, u] = await Promise.all([api.adminGetStats(), api.adminListUsers()])
      setStats(s)
      setUsers(u)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleToggleAdmin = async (id) => {
    try {
      await api.adminToggleAdmin(id)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (id, email) => {
    if (!window.confirm(`¿Eliminar la cuenta de ${email}? Esto borra también sus conversaciones y archivos.`)) return
    try {
      await api.adminDeleteUser(id)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <div className="center-msg">Cargando panel de administrador…</div>

  return (
    <>
      <section className="panel-hero page-section" style={{ paddingBottom: 20 }}>
        <div className="wrap">
          <div className="eyebrow">Solo administradores</div>
          <h1>Panel de administración</h1>
          {error && <p className="error">{error}</p>}
          {stats && (
            <div className="panel-stats">
              <div className="stat"><strong>{stats.total_users}</strong><span>Docentes registrados</span></div>
              <div className="stat"><strong>{stats.new_users_7d}</strong><span>Nuevos esta semana</span></div>
              <div className="stat"><strong>{stats.total_sessions}</strong><span>Conversaciones totales</span></div>
              <div className="stat"><strong>{stats.total_messages}</strong><span>Mensajes totales</span></div>
              <div className="stat"><strong>{stats.total_files}</strong><span>Documentos totales</span></div>
              <div className="stat"><strong>{stats.pageviews_7d}</strong><span>Visitas esta semana</span></div>
            </div>
          )}
        </div>
      </section>

      <section id="configuracion" className="page-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Configuración del sitio</div>
            <h2>Apariencia y funciones</h2>
            <p>Cambia el nombre y los colores del sitio, y activa o desactiva funciones para todos los docentes.</p>
          </div>
          <SiteSettingsPanel />
        </div>
      </section>

      <section className="page-section alt-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Tráfico</div>
            <h2>Visitas por día (últimos 7 días)</h2>
          </div>
          <div className="agenda-panel">
            {stats && <BarChart data={stats.pageviews_by_day} labelKey="date" valueKey="views" />}
          </div>
          {stats && stats.top_paths.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <div className="eyebrow">Páginas más visitadas</div>
              <div className="topic-list" style={{ marginTop: 12 }}>
                {stats.top_paths.map((p, i) => (
                  <div key={i} className="topic-row" style={{ cursor: 'default' }}>
                    <span className="topic-dot"></span>
                    <div className="topic-main">
                      <div className="topic-title">{p.path}</div>
                    </div>
                    <span className="topic-date">{p.views} visitas</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="page-section">
        <div className="wrap">
          <div className="section-head">
            <div className="eyebrow">Cuentas</div>
            <h2>Docentes</h2>
          </div>
          <div className="topic-list">
            {users.map((u) => (
              <div key={u.id} className="topic-row" style={{ cursor: 'default' }}>
                <span className="topic-dot"></span>
                <div className="topic-main">
                  <div className="topic-materia">{u.is_admin ? 'ADMIN' : 'DOCENTE'}</div>
                  <div className="topic-title">{u.full_name || u.email}</div>
                  <div className="topic-meta">{u.email} · {u.session_count} conversaciones · {u.file_count} archivos</div>
                </div>
                <span className="topic-date">{formatDate(u.created_at)}</span>
                {u.id !== user.id && (
                  <>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleToggleAdmin(u.id)}>
                      {u.is_admin ? 'Quitar admin' : 'Hacer admin'}
                    </button>
                    <button className="topic-del" aria-label="Eliminar usuario" onClick={() => handleDelete(u.id, u.email)}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
