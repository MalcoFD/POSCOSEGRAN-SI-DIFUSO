import { lazy, Suspense, useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider, useIsFetching, useQuery } from '@tanstack/react-query'
import { createRootRoute, createRoute, createRouter, RouterProvider, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import Sidebar from './components/Sidebar'
import Dashboard from './views/Dashboard'
import Evaluacion from './views/Evaluacion'
import Resultado from './views/Resultado'
import Seguimiento from './views/Seguimiento'
import Almacenes from './views/Almacenes'
import Revision from './views/Revision'
import Login from './views/Login'
import { accessToken, iniciales, localAuth, nombre, request, supabase, NOTA_PROTOTIPO, type Schema } from './api/client'
import { ErrorMessage, Skeleton, SkeletonPage } from './components/Shared'
import { ToastProvider } from './components/Toast'
import { IconSearch } from './components/Icons'
import type { View } from './types'

// Vistas de uso ocasional: se descargan al abrirlas.
const Conocimiento = lazy(() => import('./views/Conocimiento'))
const Adquisicion = lazy(() => import('./views/Adquisicion'))
const Configuracion = lazy(() => import('./views/Configuracion'))

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: true, staleTime: 15000 } } })
export const paths: Record<View, string> = { dashboard: '/', evaluacion: '/evaluacion', resultado: '/resultado', seguimiento: '/seguimiento', almacenes: '/almacenes', revision: '/revision', conocimiento: '/conocimiento', adquisicion: '/adquisicion', configuracion: '/configuracion' }
const titulos: Record<View, string> = { dashboard: 'Inicio', evaluacion: 'Evaluar unidad', resultado: 'Resultado', seguimiento: 'Seguimiento', almacenes: 'Almacenes y lotes', revision: 'Revisión técnica', conocimiento: 'Base de conocimiento', adquisicion: 'Adquisición', configuracion: 'Configuración' }
export function useAppNavigate() {
  const navigate = useNavigate()
  return (view: View, id?: string, paso?: number) => { void navigate({ to: paths[view], search: id ? { id, ...(paso ? {paso} : {}) } : {} }); window.scrollTo(0, 0) }
}
export function useId() { return useRouterState({ select: s => (s.location.search as { id?: string }).id }) }
export function usePaso() { return useRouterState({ select: s => (s.location.search as { paso?: number }).paso }) }
const esMovil = () => window.innerWidth < 768

function Shell() {
  const [logged, setLogged] = useState<boolean | null>(null)
  const [collapsed, setCollapsed] = useState(esMovil())
  const navigate = useAppNavigate()
  const path = useRouterState({ select: s => s.location.pathname })
  const perfil = useQuery({ queryKey: ['perfil'], queryFn: () => request<Schema['Perfil']>('/me'), enabled: logged === true })
  const sincronizando = useIsFetching() > 0
  const active = (Object.keys(paths) as View[]).find(v => paths[v] === path)
  useEffect(() => {
    const anchoMovil = window.matchMedia('(max-width: 767px)')
    const ajustar = () => { if (anchoMovil.matches) setCollapsed(true) }
    anchoMovil.addEventListener('change', ajustar)
    return () => anchoMovil.removeEventListener('change', ajustar)
  }, [])
  useEffect(() => {
    void accessToken().then(token => setLogged(!!token))
    const listener = supabase?.auth.onAuthStateChange((event, session) => {
      setLogged(!!session); if (event === 'SIGNED_OUT') queryClient.clear()
    })
    return () => listener?.data.subscription.unsubscribe()
  }, [])
  useEffect(() => {
    document.title = logged === false ? 'Iniciar sesión · POSCOSEGRAN' : `${active ? titulos[active] : 'Página no encontrada'} · POSCOSEGRAN`
  }, [active, logged])
  async function logout() {
    if (localAuth) sessionStorage.removeItem('poscosegran-session')
    else await supabase?.auth.signOut()
    queryClient.clear(); setLogged(false)
  }
  if (logged === null) return <main><SkeletonPage label="Verificando la sesión…" /></main>
  if (!logged) return <Login onLogin={() => { queryClient.clear(); setLogged(true) }} />
  const nombreUsuario = perfil.data?.nombre || 'Sesión'
  return <div className="app-shell">
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <Sidebar activeView={active ?? 'dashboard'} onNavigate={view => { navigate(view); if (esMovil()) setCollapsed(true) }} collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} roles={perfil.data?.roles || []} cargando={perfil.isLoading} />
    {!collapsed && esMovil() && <button className="sidebar-backdrop" aria-label="Cerrar menú" onClick={() => setCollapsed(true)} />}
    <div className="app-content" style={{ marginLeft: collapsed ? 64 : 240 }}>
      <header className="topbar">
        <span className="muted desktop-only" style={{ fontSize: 14 }}>Sistema difuso Mamdani para la gestión poscosecha</span>
        <div className="topbar-user">
          {sincronizando && !perfil.isLoading && <span className="sync-dot" title="Actualizando datos"><span className="sr-only">Actualizando datos</span></span>}
          {perfil.isLoading ? <><Skeleton className="sk-circle" width={36} height={36} /><div><Skeleton width={110} height={12} /><Skeleton width={64} height={10} /></div></> : <>
            <span className="avatar" aria-hidden="true">{iniciales(nombreUsuario)}</span>
            <div><strong>{nombreUsuario}</strong><span className="topbar-roles">{perfil.data?.roles.map(r => <span key={r} className="badge">{nombre(r)}</span>)}{localAuth && import.meta.env.DEV && <span className="badge info">Desarrollo local</span>}</span></div>
          </>}
          <button onClick={() => void logout()}>Cerrar sesión</button>
        </div>
      </header>
      <main id="contenido" tabIndex={-1}>
        <ErrorMessage error={perfil.error} onRetry={() => void perfil.refetch()} />
        {perfil.isLoading ? <SkeletonPage metrics /> : perfil.data && <Suspense fallback={<SkeletonPage />}><Outlet /></Suspense>}
      </main>
      <footer>POSCOSEGRAN · {NOTA_PROTOTIPO}</footer>
    </div>
  </div>
}

function NoEncontrada() {
  const navigate = useAppNavigate()
  return <div className="not-found">
    <div className="empty-icon"><IconSearch size={34} /></div>
    <p className="eyebrow mono">Error 404</p>
    <h1>Página no encontrada</h1>
    <p className="muted">La dirección no existe o la unidad ya no está asignada a tu cuenta. Tus capturas guardadas siguen disponibles.</p>
    <div className="actions"><button className="primary" onClick={() => navigate('dashboard')}>Ir al inicio</button><button onClick={() => navigate('almacenes')}>Ver almacenes</button></div>
  </div>
}

const root = createRootRoute({ component: Shell, notFoundComponent: NoEncontrada })
const validateSearch = (s: Record<string, unknown>): { id?: string; paso?: number } => ({ ...(typeof s.id === 'string' ? {id:s.id} : {}), ...(Number.isInteger(s.paso) && Number(s.paso) >= 1 && Number(s.paso) <= 10 ? {paso:Number(s.paso)} : {}) })
const children = [
  createRoute({ getParentRoute: () => root, path: '/', component: Dashboard }),
  createRoute({ getParentRoute: () => root, path: '/evaluacion', validateSearch, component: Evaluacion }),
  createRoute({ getParentRoute: () => root, path: '/resultado', validateSearch, component: Resultado }),
  createRoute({ getParentRoute: () => root, path: '/seguimiento', validateSearch, component: Seguimiento }),
  createRoute({ getParentRoute: () => root, path: '/almacenes', component: Almacenes }),
  createRoute({ getParentRoute: () => root, path: '/revision', component: Revision }),
  createRoute({ getParentRoute: () => root, path: '/conocimiento', component: Conocimiento }),
  createRoute({ getParentRoute: () => root, path: '/adquisicion', component: Adquisicion }),
  createRoute({ getParentRoute: () => root, path: '/configuracion', component: Configuracion }),
]
const router = createRouter({ routeTree: root.addChildren(children) })
export default function App() { return <QueryClientProvider client={queryClient}><ToastProvider><RouterProvider router={router} /></ToastProvider></QueryClientProvider> }
