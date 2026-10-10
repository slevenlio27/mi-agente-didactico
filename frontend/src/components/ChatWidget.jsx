import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import { useAuthModal } from '../AuthModalContext'
import { useChatWidget } from '../ChatWidgetContext'
import PreferencesModal, { getDefaultProvider } from './PreferencesModal'
import KeySetupCard from './KeySetupCard'
import { enabledProviders, useSiteSettings } from '../SiteSettingsContext'

const PROVIDER_LABELS = { anthropic: 'Claude', openai: 'ChatGPT', gemini: 'Gemini' }

export default function ChatWidget() {
  const { user } = useAuth()
  const { open: openAuthModal } = useAuthModal()
  const { isOpen, openWidget, closeWidget, activeSessionId, setActiveSessionId, notifyRefresh } = useChatWidget()
  const { settings } = useSiteSettings()
  const defaultProvider = () => getDefaultProvider(enabledProviders(settings))

  const [session, setSession] = useState(null)
  const [loadingSession, setLoadingSession] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [pendingFiles, setPendingFiles] = useState([])
  const [keyStatus, setKeyStatus] = useState(null)
  const [keyInvalid, setKeyInvalid] = useState(false)
  const [prefsOpen, setPrefsOpen] = useState(false)
  const bodyRef = useRef(null)
  const textRef = useRef(null)
  const fileInputRef = useRef(null)

  // Gate: si alguien intenta abrir el widget sin sesión iniciada, pedimos login en su lugar.
  const handleLauncherClick = () => {
    if (!user) {
      openAuthModal()
      return
    }
    isOpen ? closeWidget() : openWidget()
  }

  // Cuando el widget se abre para un usuario autenticado, aseguramos una sesión activa.
  useEffect(() => {
    if (!settings.chat_enabled) return
    if (!isOpen || !user) return
    let cancelled = false

    async function ensureSession() {
      setLoadingSession(true)
      setError('')
      try {
        if (activeSessionId) {
          const data = await api.getSession(activeSessionId)
          if (!cancelled) setSession(data)
        } else {
          const sessions = await api.listSessions()
          if (sessions.length > 0) {
            const data = await api.getSession(sessions[0].id)
            if (!cancelled) {
              setSession(data)
              setActiveSessionId(data.id)
            }
          } else {
            const created = await api.createSession(defaultProvider())
            if (!cancelled) {
              setSession({ ...created, messages: [] })
              setActiveSessionId(created.id)
            }
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoadingSession(false)
      }
    }
    ensureSession()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, user, activeSessionId, settings.chat_enabled])

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [session, sending])

  const startNewConversation = async () => {
    setError('')
    try {
      const created = await api.createSession(defaultProvider())
      setSession({ ...created, messages: [] })
      setActiveSessionId(created.id)
      notifyRefresh()
    } catch (err) {
      setError(err.message)
    }
  }

  // Qué claves tiene el docente y si el servidor tiene la suya (solo sí/no).
  const refreshKeyStatus = () => api.getApiKeysStatus().then(setKeyStatus).catch(() => {})
  useEffect(() => { if (isOpen && user) refreshKeyStatus() }, [isOpen, user])

  const provider = session?.provider
  const needsKey = Boolean(keyStatus && provider && !keyStatus[`has_${provider}_key`] && !keyStatus[`server_has_${provider}_key`])
  const showKeyCard = needsKey || keyInvalid

  const handleKeySaved = () => { setKeyInvalid(false); setError(''); refreshKeyStatus() }

  const handleSend = async () => {
    const files = pendingFiles
    // Se puede enviar solo un archivo, sin texto: la pregunta por defecto pide analizarlo
    const content = input.trim() || (files.length ? 'Analiza el archivo adjunto.' : '')
    if (!content || sending || !session) return
    setSending(true)
    setError('')
    setInput('')
    setSession((s) => ({ ...s, messages: [...s.messages, { id: 'tmp', role: 'user', content, files }] }))
    try {
      await api.sendMessage(session.id, content, files.map((f) => f.id))
      setPendingFiles([])
      const fresh = await api.getSession(session.id)
      setSession(fresh)
      notifyRefresh()
    } catch (err) {
      if (/no es válida/i.test(err.message)) setKeyInvalid(true)
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  const handleTextareaInput = (e) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px'
  }

  const handleFilePick = async (e) => {
    const files = Array.from(e.target.files || [])
    for (const file of files) {
      try {
        const uploaded = await api.uploadFile(file, session?.id)
        setPendingFiles((prev) => [...prev, uploaded])
      } catch (err) {
        setError(err.message)
      }
    }
    e.target.value = ''
  }

  // El admin apagó el asistente: no se muestra en ninguna parte del sitio.
  if (!settings.chat_enabled) return null

  if (!user) {
    return (
      <button id="chat-launcher" aria-label="Abrir asistente" aria-expanded="false" onClick={handleLauncherClick}>
        <svg viewBox="0 0 24 24" fill="none"><path d="M4 5c3-1.5 6-1.5 8 0v14c-2-1.5-5-1.5-8 0V5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"></path><path d="M20 5c-3-1.5-6-1.5-8 0v14c2-1.5 5-1.5 8 0V5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" opacity=".55"></path></svg>
      </button>
    )
  }

  return (
    <>
      <button id="chat-launcher" aria-label="Abrir asistente" aria-expanded={isOpen} onClick={handleLauncherClick}>
        <svg viewBox="0 0 24 24" fill="none"><path d="M4 5c3-1.5 6-1.5 8 0v14c-2-1.5-5-1.5-8 0V5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"></path><path d="M20 5c-3-1.5-6-1.5-8 0v14c2-1.5 5-1.5 8 0V5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" opacity=".55"></path></svg>
      </button>

      <div id="chat-panel" className={isOpen ? 'open' : ''} data-provider={session?.provider || ''} role="dialog" aria-label={settings.site_name}>
        <div className="chat-head">
          <div className="ct">
            {settings.site_name}
            <span className="status">{PROVIDER_LABELS[session?.provider] || '···'} · {loadingSession ? 'cargando' : 'listo'}</span>
          </div>
          <div className="chat-head-actions">
            <button aria-label="Nueva conversación" title="Nueva conversación" onClick={startNewConversation}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><path d="M12 5v14M5 12h14"></path></svg>
            </button>
            <button aria-label="Preferencias de IA" title="Preferencias de IA" onClick={() => setPrefsOpen(true)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="3"></circle><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"></path></svg>
            </button>
            <button aria-label="Cerrar" onClick={closeWidget}>✕</button>
          </div>
        </div>

        <div id="chat-body" ref={bodyRef}>
          {(!session || session.messages.length === 0) && !loadingSession && (
            <div className="msg bot">Hola, profesor/a. Sube un programa de curso, una rúbrica o una lectura, y le ayudo a analizarla y a planificar sus actividades de clase. También puede escribirme directamente.</div>
          )}
          {session?.messages.map((m) => (
            <div key={m.id} className={`msg ${m.role === 'user' ? 'user' : 'bot'}`}>
              {m.files?.length > 0 && (
                <div className="msg-files">
                  {m.files.map((f) => <span key={f.id} className="msg-file" title={f.original_name}>📎 {f.original_name}</span>)}
                </div>
              )}
              {m.content}
            </div>
          ))}
          {sending && (
            <div className="msg typing"><span></span><span></span><span></span></div>
          )}
          {showKeyCard && session && (
            <KeySetupCard provider={provider} ownKeysAllowed={settings.own_api_keys_enabled}
              invalid={keyInvalid} onSaved={handleKeySaved} />
          )}
          {error && !keyInvalid && <div className="msg err">{error}</div>}
        </div>

        {pendingFiles.length > 0 && (
          <div id="chat-attachments">
            {pendingFiles.map((f) => (
              <div key={f.id} className="pending-file">
                <span>{f.original_name}</span>
                <button aria-label={`Quitar ${f.original_name}`} onClick={() => setPendingFiles((prev) => prev.filter((x) => x.id !== f.id))}>✕</button>
              </div>
            ))}
          </div>
        )}

        <div className="chat-input-row">
          {settings.uploads_enabled && (
            <>
              <button className="icon-btn" aria-label="Adjuntar archivo" title="Adjuntar archivo" onClick={() => fileInputRef.current?.click()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="m20 12-8 8a5 5 0 0 1-7-7l8-8a3.5 3.5 0 0 1 5 5l-8 8a2 2 0 0 1-3-3l8-8"></path></svg>
              </button>
              <input ref={fileInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.md" multiple hidden onChange={handleFilePick} />
            </>
          )}
          <textarea
            ref={textRef}
            rows={1}
            placeholder="Escriba su pregunta…"
            aria-label="Mensaje"
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            disabled={sending || loadingSession || needsKey}
          />
          <button className="icon-btn send" aria-label="Enviar" onClick={handleSend} disabled={sending || loadingSession || needsKey || (!input.trim() && pendingFiles.length === 0)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="m3 11 18-8-8 18-2.5-7.5L3 11Z"></path><path d="M10.5 13.5 21 3"></path></svg>
          </button>
        </div>
        <div className="chat-hint">PDF, imágenes o texto · el asistente puede equivocarse, revise antes de usarlo en clase</div>
      </div>

      <PreferencesModal open={prefsOpen} onClose={() => setPrefsOpen(false)} />
    </>
  )
}
