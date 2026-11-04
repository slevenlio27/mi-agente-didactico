import { Suspense, lazy, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AuthModal from './components/AuthModal'
import ChatWidget from './components/ChatWidget'
import CookieBanner from './components/CookieBanner'
import MobileDrawer from './components/MobileDrawer'
import SiteNav from './components/SiteNav'
import { AuthModalProvider } from './AuthModalContext'
import { AuthProvider, useAuth } from './AuthContext'
import { ChatWidgetProvider } from './ChatWidgetContext'
import { ThemeProvider } from './ThemeContext'
import { SiteSettingsProvider, useSiteSettings } from './SiteSettingsContext'
import { api } from './api'

// Code-splitting: cada página se descarga solo cuando se visita, así la
// carga inicial (la landing, que es lo primero que ve casi todo el mundo)
// no arrastra el código del panel docente ni del panel de administrador.
// La portada es la página más visitada: se incluye desde el inicio (sin una segunda descarga)
import Landing from './pages/Landing'
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const Admin = lazy(() => import('./pages/Admin'))
const Legal = lazy(() => import('./pages/Legal'))

function PageLoading() {
  return <div className="center-msg">Cargando…</div>
}

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <PageLoading />
  return user ? children : <Navigate to="/" replace />
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <PageLoading />
  return user?.is_admin ? children : <Navigate to="/" replace />
}

function PageviewTracker() {
  const location = useLocation()
  const { settings } = useSiteSettings()
  useEffect(() => {
    if (settings.analytics_enabled) api.logPageview(location.pathname)
  }, [location.pathname, settings.analytics_enabled])
  return null
}

function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <>
      <PageviewTracker />
      <SiteNav onOpenDrawer={() => setDrawerOpen(true)} />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      <main id="contenido">
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/panel" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
          <Route path="/legal" element={<Legal />} />
          <Route path="/restablecer" element={<ResetPassword />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
      </main>

      <AuthModal />
      <ChatWidget />
      <CookieBanner />
    </>
  )
}

export default function App() {
  return (
    <SiteSettingsProvider>
    <ThemeProvider>
      <AuthProvider>
        <AuthModalProvider>
          <ChatWidgetProvider>
            <AppShell />
          </ChatWidgetProvider>
        </AuthModalProvider>
      </AuthProvider>
    </ThemeProvider>
    </SiteSettingsProvider>
  )
}
