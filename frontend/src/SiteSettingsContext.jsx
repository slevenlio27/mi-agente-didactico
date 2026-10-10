import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api'

// Valores usados mientras carga la configuración (o si el backend no responde),
// para que el sitio nunca se vea roto. Coinciden con los del servidor.
export const DEFAULT_SETTINGS = {
  google_client_id: null,
  site_name: 'Mi Agente Didáctico',
  accent_light: '#1f8a73',
  accent_dark: '#5fcdb1',
  chat_color_anthropic: null,
  chat_color_openai: null,
  chat_color_gemini: null,
  materia_colors_enabled: true,
  registration_enabled: true,
  google_login_enabled: true,
  chat_enabled: true,
  uploads_enabled: true,
  agenda_enabled: true,
  own_api_keys_enabled: true,
  provider_anthropic_enabled: false,
  provider_openai_enabled: false,
  provider_gemini_enabled: true,
  analytics_enabled: true,
  cookie_banner_enabled: true,
}

const HEX = /^#[0-9a-fA-F]{6}$/

/** Aplica colores y nombre al documento. Se usa también para la vista previa en vivo del panel de admin. */
export function applySiteAppearance(s) {
  const root = document.documentElement
  const setColor = (name, value) => {
    // Doble control: el servidor ya valida, pero solo se aplica "#rrggbb".
    if (value && HEX.test(value)) root.style.setProperty(name, value)
    else root.style.removeProperty(name)
  }
  setColor('--brand-accent-light', s.accent_light)
  setColor('--brand-accent-dark', s.accent_dark)
  setColor('--chat-anthropic', s.chat_color_anthropic)
  setColor('--chat-openai', s.chat_color_openai)
  setColor('--chat-gemini', s.chat_color_gemini)
  if (s.site_name) document.title = s.site_name
}

const PROVIDER_NAMES = { anthropic: 'Claude', openai: 'ChatGPT', gemini: 'Gemini' }

/** Nombres legibles de las IA activas, p. ej. "Gemini" o "Claude, ChatGPT o Gemini". */
export function providerNames(s, joiner = 'o') {
  const n = enabledProviders(s).map((p) => PROVIDER_NAMES[p])
  return n.length <= 1 ? (n[0] || '') : `${n.slice(0, -1).join(', ')} ${joiner} ${n[n.length - 1]}`
}

export function enabledProviders(s) {
  return ['anthropic', 'openai', 'gemini'].filter((p) => s[`provider_${p}_enabled`])
}

const SiteSettingsContext = createContext({ settings: DEFAULT_SETTINGS, refresh: () => {} })

export function SiteSettingsProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)

  const refresh = useCallback(async () => {
    try {
      const s = await api.getPublicSettings()
      setSettings({ ...DEFAULT_SETTINGS, ...s })
    } catch {
      /* si falla, se quedan los valores por defecto */
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { applySiteAppearance(settings) }, [settings])

  return (
    <SiteSettingsContext.Provider value={{ settings, refresh }}>
      {children}
    </SiteSettingsContext.Provider>
  )
}

export function useSiteSettings() {
  return useContext(SiteSettingsContext)
}
