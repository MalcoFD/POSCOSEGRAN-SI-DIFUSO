import { useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { createRootRoute, createRoute, createRouter, RouterProvider, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import Sidebar from './components/Sidebar'
import Dashboard from './views/Dashboard'
import Configuracion from './views/Configuracion'
import Evaluacion from './views/Evaluacion'
import Resultado from './views/Resultado'
import Seguimiento from './views/Seguimiento'
import Conocimiento from './views/Conocimiento'
import Almacenes from './views/Almacenes'
import Revision from './views/Revision'
import Adquisicion from './views/Adquisicion'
import Login from './views/Login'
import { accessToken, localAuth, request, supabase, NOTA_PROTOTIPO, type Schema } from './api/client'
import { ErrorMessage, Loading } from './components/Shared'
import type { View } from './types'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: true, staleTime: 15000 } } })
export const paths: Record<View, string> = { dashboard: '/', evaluacion: '/evaluacion', resultado: '/resultado', seguimiento: '/seguimiento', almacenes: '/almacenes', revision: '/revision', conocimiento: '/conocimiento', adquisicion: '/adquisicion', configuracion: '/configuracion' }
export function useAppNavigate() {
  const navigate = useNavigate()
  return (view: View, id?: string, paso?: number) => { void navigate({ to: paths[view], search: id ? { id, ...(paso ? {paso} : {}) } : {} }); window.scrollTo(0, 0) }
}
export function useId() { return useRouterState({ select: s => (s.location.search as { id?: string }).id }) }
export function usePaso() { return useRouterState({ select: s => (s.location.search as { paso?: number }).paso }) }
function Shell() {
  const [logged, setLogged] = useState<boolean | null>(null)
  const [collapsed, setCollapsed] = useState(window.innerWidth < 768)
  const navigate = useAppNavigate()
  const path = useRouterState({ select: s => s.location.pathname })
  const perfil = useQuery({ queryKey: ['perfil'], queryFn: () => request<Schema['Perfil']>('/me'), enabled: logged === true })
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
  async function logout() {
    if (localAuth) sessionStorage.removeItem('poscosegran-session')
    else await supabase?.auth.signOut()
    queryClient.clear(); setLogged(false)
  }
  if (logged === null) return <Loading />
  if (!logged) return <Login onLogin={() => { queryClient.clear(); setLogged(true) }} />
  const active = (Object.keys(paths) as View[]).find(v => paths[v] === path) || 'dashboard'
  return <div className="app-shell">
    <Sidebar activeView={active} onNavigate={view => { navigate(view); if (window.innerWidth < 768) setCollapsed(true) }} collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} roles={perfil.data?.roles || []} />
    <div className="app-content" style={{ marginLeft: collapsed ? 64 : 240 }}>
      <header className="topbar"><span className="muted desktop-only">Sistema de gestión poscosecha</span>
        <div><strong>{perfil.data?.nombre || 'Sesión'}</strong><small>{perfil.data?.roles.join(' · ')}{localAuth ? ' · Desarrollo local' : ''}</small></div>
        <button onClick={() => void logout()}>Cerrar sesión</button></header>
      <main><ErrorMessage error={perfil.error} />{perfil.isLoading ? <Loading /> : perfil.data && <Outlet />}</main>
      <footer>POSCOSEGRAN · {NOTA_PROTOTIPO}</footer>
    </div>
  </div>
}
const root = createRootRoute({ component: Shell, notFoundComponent: () => <p>Página no encontrada.</p> })
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
export default function App() { return <QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider> }
