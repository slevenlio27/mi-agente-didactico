import { createContext, useContext, useEffect, useState } from 'react'
import { useSiteSettings } from './SiteSettingsContext'

const ThemeContext = createContext(null)

export const MATERIAS = [
  { id: 'institucional', label: 'Institucional' },
  { id: 'tecnologia', label: 'Tecnología' },
  { id: 'ciencias', label: 'Ciencias' },
  { id: 'matematicas', label: 'Matemáticas' },
  { id: 'humanidades', label: 'Humanidades' },
  { id: 'derecho', label: 'Derecho' },
  { id: 'economia', label: 'Economía' },
  { id: 'arte', label: 'Arte' },
]

const THEME_KEY = 'agente_didactico_theme'
const MATERIA_KEY = 'agente_didactico_materia'

export function ThemeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem(THEME_KEY)
      if (saved) return saved === 'dark'
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      return false
    }
  })

  const [materia, setMateria] = useState(() => {
    try {
      return localStorage.getItem(MATERIA_KEY) || 'institucional'
    } catch {
      return 'institucional'
    }
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    try {
      localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light')
    } catch {
      /* localStorage no disponible: se ignora, el tema simplemente no persiste */
    }
  }, [dark])

  const { settings } = useSiteSettings()
  // Si el admin desactivó los colores por materia, todos ven el color institucional.
  const effectiveMateria = settings.materia_colors_enabled ? materia : 'institucional'

  useEffect(() => {
    document.documentElement.setAttribute('data-materia', effectiveMateria)
    try {
      localStorage.setItem(MATERIA_KEY, materia)
    } catch {
      /* idem */
    }
  }, [materia, effectiveMateria])

  return (
    <ThemeContext.Provider value={{ dark, toggleDark: () => setDark((d) => !d), materia: effectiveMateria, setMateria }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
