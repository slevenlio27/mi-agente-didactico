import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import { useChatWidget } from '../ChatWidgetContext'
import { MATERIAS, useTheme } from '../ThemeContext'
import { enabledProviders, providerNames, useSiteSettings } from '../SiteSettingsContext'

export default function Landing() {
  const { user } = useAuth()
  const { materia, setMateria } = useTheme()
  const { settings } = useSiteSettings()
  const nProviders = enabledProviders(settings).length
  const aiNames = providerNames(settings)
  const { openWidget } = useChatWidget()
  const [recentSessions, setRecentSessions] = useState([])

  useEffect(() => {
    if (!user) return
    api.listSessions().then((s) => setRecentSessions(s.slice(0, 3))).catch(() => {})
  }, [user])

  const materiaLabel = MATERIAS.find((m) => m.id === materia)?.label || 'Tecnología'

  return (
    <>
      <section className="hero">
        <div className="wrap">
          <div className="materia-bar" style={settings.materia_colors_enabled ? undefined : { display: 'none' }}>
            <div className="materia-info">
              <span className="materia-dot"></span>
              <div>
                <span className="materia-label">Estás trabajando en</span>
                <strong className="materia-current">{materiaLabel}</strong>
              </div>
            </div>
            <div className="materia-controls">
              <div className="materia-chips" role="group" aria-label="Elegir materia">
                {MATERIAS.map((m) => (
                  <button
                    key={m.id}
                    className={`materia-chip ${materia === m.id ? 'active' : ''}`}
                    onClick={() => setMateria(m.id)}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {user && recentSessions.length > 0 && (
            <div className="welcome-banner show">
              <div className="wb-text">Bienvenido de nuevo, <strong>{user.full_name || user.email}</strong>. Esto es lo último en lo que trabajaste:</div>
              <div className="wb-chips">
                {recentSessions.map((s) => (
                  <button key={s.id} className="wb-chip" onClick={() => openWidget(s.id)}>{s.title}</button>
                ))}
              </div>
            </div>
          )}

          <div className="hero-grid">
            <div>
              <div className="eyebrow">Herramienta exclusiva para docentes</div>
              <h1>Un agente que <em>revisa, planifica</em> y organiza tu material de clase.</h1>
              <p className="lead">{settings.site_name} analiza sílabos, rúbricas, lecturas y trabajos de tus estudiantes, y te devuelve una planificación de clase lista para usar. Inicia sesión para que recuerde tu historial y elige la IA con la que prefieres trabajar.</p>
              <div className="hero-cta">
                {settings.chat_enabled && <button className="btn btn-primary" onClick={() => openWidget()}>Probar el asistente</button>}
                <a href="#como-funciona" className="btn btn-ghost">Ver cómo funciona</a>
              </div>
              <div className="hero-stats">
                <div><strong>4 pasos</strong><span>De material a plan de clase</span></div>
                <div><strong>{nProviders > 1 ? `${nProviders} proveedores de IA` : `IA: ${aiNames}`}</strong><span>{nProviders > 1 ? 'Usa la que prefieras' : 'Integrada en el asistente'}</span></div>
                <div><strong>Uso docente</strong><span>Pensado para tu carga académica</span></div>
              </div>
            </div>
            <div className="ficha">
              <div className="ficha-label"><span>Ficha de planificación</span><span>N.° 214</span></div>
              <div className="ficha-title">Unidad 3 — Termodinámica</div>
              <div className="ficha-meta">Cargado: Guía_Unidad3.pdf · Rúbrica_Lab.pdf</div>
              <div className="ficha-line"></div>
              <div className="ficha-line"></div>
              <div className="ficha-line short"></div>
              <div style={{ height: 10 }}></div>
              <div className="ficha-line"></div>
              <div className="ficha-line short"></div>
              <div className="stamp-overlay"><span>Revisado por IA</span></div>
            </div>
          </div>
        </div>
      </section>

      <section id="beneficios" className="page-section">
        <div className="wrap margin-layout">
          <div>
            <div className="section-head">
              <div className="eyebrow">Por qué usarlo</div>
              <h2>Apoyo didáctico que se adapta a ti y a tu materia</h2>
              <p>El agente lee el contenido real de tu material — física, derecho, literatura, enfermería — y responde en esos términos. Si inicias sesión, además recuerda en qué estabas trabajando y con qué IA prefieres hacerlo.</p>
            </div>
            <div className="notes-main">
              <div className="note-row"><div className="glyph">Aa</div><div><h3>Mantiene el lenguaje de tu materia</h3><p>Si subes un programa de derecho procesal, el agente conserva el vocabulario técnico correcto, sin simplificar de más.</p></div></div>
              <div className="note-row"><div className="glyph">✓</div><div><h3>Convierte material en plan de clase</h3><p>Detecta objetivos, tiempos y criterios de evaluación dentro de un sílabo, y los convierte en una secuencia de actividades.</p></div></div>
              <div className="note-row"><div className="glyph"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="8" r="3.5"></circle><path d="M5 20c.8-3 3.5-4.5 7-4.5s6.2 1.5 7 4.5"></path></svg></div><div><h3>Recuerda tu historial</h3><p>Con tu cuenta iniciada, el sitio te saluda por tu nombre y te muestra tus últimas planificaciones al volver.</p></div></div>
              <div className="note-row"><div className="glyph">⇄</div><div><h3>{nProviders > 1 ? 'Usa la IA que prefieras' : `Impulsado por ${aiNames}`}</h3><p>{nProviders > 1 ? `Puedes elegir entre ${aiNames} para tus conversaciones.` : `Las conversaciones del asistente usan ${aiNames}.`}</p></div></div>
            </div>
          </div>
          <aside className="margin-col">
            <div className="stamp-note">verificar<br/>fecha límite</div>
            <div className="stamp-note">ajustar a<br/>90 minutos</div>
            <div className="stamp-note">revisar<br/>rúbrica</div>
          </aside>
        </div>
      </section>

      <section id="que-hace" className="page-section" style={{ background: 'var(--fg-soft)' }}>
        <div className="wrap">
          <div className="section-head"><div className="eyebrow">Qué puede hacer por ti</div><h2>Sube el material de tu curso, recibe trabajo listo para el aula</h2></div>
          <div className="catalog-grid">
            <div className="catalog-card"><span className="tab">Planificación</span><h3>Secuencias de clase</h3><ul><li>Sube tu programa o guía de unidad</li><li>Recibe una secuencia de sesiones con objetivos y tiempos</li><li>Pide ajustes si cambia el calendario académico</li></ul></div>
            <div className="catalog-card"><span className="tab">Evaluación</span><h3>Rúbricas y exámenes</h3><ul><li>Sube una rúbrica o examen anterior</li><li>Recibe preguntas de repaso alineadas a tus criterios</li><li>Detecta vacíos entre lo enseñado y lo evaluado</li></ul></div>
            <div className="catalog-card"><span className="tab">Contenidos</span><h3>Lecturas y materiales</h3><ul><li>Sube un artículo, capítulo o set de diapositivas</li><li>Recibe un resumen de los puntos clave para tu clase</li><li>Pide ideas de actividades basadas en ese material</li></ul></div>
          </div>
        </div>
      </section>

      <section id="como-funciona" className="page-section">
        <div className="wrap" style={{ maxWidth: 820 }}>
          <div className="section-head"><div className="eyebrow">Cómo funciona</div><h2>De un archivo de curso a un plan de clase, en cuatro pasos</h2></div>
          <div className="timeline">
            <div className="tl-step"><div className="tl-num">1</div><div><h3>Inicia sesión</h3><p>Con correo y contraseña o con tu cuenta de Google, para que el sitio recuerde tu historial y tus preferencias de IA entre visitas.</p></div></div>
            <div className="tl-step"><div className="tl-num">2</div><div><h3>Sube tu material</h3><p>Adjunta un PDF del programa, una rúbrica, un artículo o una imagen de tus apuntes de clase.</p></div></div>
            <div className="tl-step"><div className="tl-num">3</div><div><h3>El agente lo analiza</h3><p>Identifica objetivos, fechas de evaluación y nivel de dificultad, usando el proveedor de IA que hayas elegido.</p></div></div>
            <div className="tl-step"><div className="tl-num">4</div><div><h3>Obtienes tu plan</h3><p>Una secuencia de actividades lista para el aula, guardada en tu historial para retomarla cuando quieras.</p></div></div>
          </div>
        </div>
      </section>

      {settings.chat_enabled && (
      <section id="asistente" className="page-section">
        <div className="wrap">
          <div className="chat-showcase">
            <div>
              <div className="eyebrow">Asistente integrado</div>
              <h2>Conversa con tu material de clase, con la IA que prefieras</h2>
              <p>El panel de chat está disponible en cualquier página del sitio. Sube un archivo de tu curso y pídele ayuda para planificar la próxima clase.</p>
              <ul className="feature-list">
                <li>Analiza PDF, imágenes y texto plano</li>
                <li>{nProviders > 1 ? `Elige entre ${aiNames}` : `Respuestas generadas con ${aiNames}`}</li>
                <li>Propone secuencias de actividades con tiempos</li>
                <li>Guarda tu historial si iniciaste sesión</li>
              </ul>
              <button className="btn btn-primary" style={{ marginTop: 28 }} onClick={() => openWidget()}>Abrir el asistente ahora</button>
            </div>
            <div className="mini-preview">
              <div className="mp-head"><span className="mp-dot"></span><span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '.08em' }}>vista previa</span></div>
              <div className="mini-msg bot">Subiste "Programa_Termodinamica.pdf". La unidad 3 tiene 4 sesiones y un laboratorio evaluado con rúbrica.</div>
              <div className="mini-msg user">Perdí una sesión por un feriado, ¿cómo la reorganizo?</div>
              <div className="mini-msg bot">Sugiero fusionar la introducción teórica con la sesión 2 y mover el laboratorio a la semana siguiente. ¿Reviso la rúbrica para confirmar tiempos?</div>
            </div>
          </div>
        </div>
      </section>
      )}

      <footer className="site-footer">
        <div className="wrap">
          <span>Mi Agente Didáctico — apoyo con IA exclusivo para docentes universitarios</span>
          <nav className="footer-legal-links">
            <Link to="/legal#privacidad">Privacidad</Link>
            <Link to="/legal#terminos">Términos</Link>
            <Link to="/legal#cookies">Cookies</Link>
          </nav>
        </div>
      </footer>
    </>
  )
}
