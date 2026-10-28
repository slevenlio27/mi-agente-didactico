import { createContext, useContext, useState } from 'react'

const ChatWidgetContext = createContext(null)

export function ChatWidgetProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(null)
  // Se incrementa cada vez que el widget crea/actualiza una sesión, para que
  // otras vistas (el panel docente) sepan que deben recargar su lista.
  const [refreshSignal, setRefreshSignal] = useState(0)
  // «Planificar con IA» desde la galería: el chat abre una conversación nueva y analiza el archivo
  const [planRequest, setPlanRequest] = useState(null)
  const requestPlanning = (file) => { setPlanRequest({ file, n: Date.now() }); setIsOpen(true) }
  const clearPlanRequest = () => setPlanRequest(null)

  const openWidget = (sessionId = null) => {
    if (sessionId) setActiveSessionId(sessionId)
    setIsOpen(true)
  }
  const closeWidget = () => setIsOpen(false)
  const notifyRefresh = () => setRefreshSignal((n) => n + 1)

  return (
    <ChatWidgetContext.Provider
      value={{ isOpen, openWidget, closeWidget, activeSessionId, setActiveSessionId, refreshSignal, notifyRefresh, planRequest, requestPlanning, clearPlanRequest }}
    >
      {children}
    </ChatWidgetContext.Provider>
  )
}

export function useChatWidget() {
  return useContext(ChatWidgetContext)
}
