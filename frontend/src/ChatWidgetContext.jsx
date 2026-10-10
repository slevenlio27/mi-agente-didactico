import { createContext, useContext, useState } from 'react'

const ChatWidgetContext = createContext(null)

export function ChatWidgetProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(null)
  // Se incrementa cada vez que el widget crea/actualiza una sesión, para que
  // otras vistas (el panel docente) sepan que deben recargar su lista.
  const [refreshSignal, setRefreshSignal] = useState(0)

  const openWidget = (sessionId = null) => {
    if (sessionId) setActiveSessionId(sessionId)
    setIsOpen(true)
  }
  const closeWidget = () => setIsOpen(false)
  const notifyRefresh = () => setRefreshSignal((n) => n + 1)

  return (
    <ChatWidgetContext.Provider
      value={{ isOpen, openWidget, closeWidget, activeSessionId, setActiveSessionId, refreshSignal, notifyRefresh }}
    >
      {children}
    </ChatWidgetContext.Provider>
  )
}

export function useChatWidget() {
  return useContext(ChatWidgetContext)
}
