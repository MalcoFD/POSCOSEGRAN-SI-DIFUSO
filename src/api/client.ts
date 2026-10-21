import { createClient } from '@supabase/supabase-js'
import type { components } from './contrato'

export type Schema = components['schemas']
export type Unidad = Schema['Unidad']
export type EvaluacionEntrada = Schema['EvaluacionEntrada-Input']
export type Observacion = Schema['ObservacionEntrada']
export type Resultado = Schema['ResultadoEvaluacion']
export const localAuth = import.meta.env.VITE_AUTH_MODE === 'local'
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY
export const supabase = !localAuth && supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey) : null
export const baseUrl = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number, message: string, public requestId?: string) { super(message) }
}

export async function accessToken(): Promise<string | null> {
  if (localAuth) {
    const raw = sessionStorage.getItem('poscosegran-session')
    if (!raw) return null
    try {
      const session = JSON.parse(raw) as { access_token: string; expires_at: number }
      return session.expires_at > Date.now() / 1000 ? session.access_token : null
    } catch { return null }
  }
  return (await supabase?.auth.getSession())?.data.session?.access_token || null
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await accessToken()
  if (!token) throw new ApiError(401, 'Inicia sesión para continuar. Tu captura se conserva.')
  const response = await fetch(baseUrl + path, {
    ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.campos?.map((f: {ruta: string; mensaje: string}) => `${f.ruta}: ${f.mensaje}`).join('; ')
    throw new ApiError(response.status, `${data?.mensaje || data?.detail || 'No se pudo completar la operación'}${detail ? ': ' + detail : ''}`, data?.id_solicitud)
  }
  return data as T
}

// Mantiene la misma clave en reintentos de una operación de resultado incierto.
export async function write<T>(path: string, body: unknown, method = 'POST', headers: Record<string, string> = {}): Promise<T> {
  const signature = `${method}:${path}:${JSON.stringify(body)}`
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(signature))
  const storageKey = 'operacion:' + Array.from(new Uint8Array(digest), v => v.toString(16).padStart(2, '0')).join('')
  const key = sessionStorage.getItem(storageKey) || crypto.randomUUID()
  sessionStorage.setItem(storageKey, key)
  try {
    const result = await request<T>(path, { method, body: JSON.stringify(body), headers: { 'Idempotency-Key': key, ...headers } })
    sessionStorage.removeItem(storageKey)
    return result
  } catch (error) {
    if (error instanceof ApiError && error.status < 500 && error.status !== 429) sessionStorage.removeItem(storageKey)
    throw error
  }
}

export async function list<T>(path: string): Promise<T[]> {
  const items: T[] = []
  let cursor: string | null = null
  do {
    const page: { items: T[]; siguiente_cursor: string | null } = await request(
      `${path}${path.includes('?') ? '&' : '?'}limite=100${cursor ? '&cursor=' + encodeURIComponent(cursor) : ''}`,
    )
    items.push(...page.items)
    cursor = page.siguiente_cursor
  } while (cursor)
  return items
}

export const revisiones = (u: Unidad) => ({ revision_unidad: u.revision, revision_almacen: u.revision_almacen })
const formatoFecha = new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
export const fecha = (value: string | null) => value ? formatoFecha.format(new Date(value)) : 'Sin registro'
const relativo = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })
/** "Mañana", "En 6 días", "Hace 2 horas"; complementa a fecha(), no la sustituye. */
export function fechaRelativa(value: string | null, ahora = Date.now()) {
  if (!value) return 'Sin programar'
  const ms = new Date(value).getTime() - ahora
  const horas = ms / 3_600_000
  const texto = Math.abs(horas) < 24 ? relativo.format(Math.round(horas), 'hour') : relativo.format(Math.round(horas / 24), 'day')
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

// Etiquetas legibles de los enums de la API; el valor enviado no cambia.
export const ETIQUETAS: Record<string, string> = {
  VIGENTE: 'Vigente', VENCIDA: 'Vencida', INVALIDADA: 'Invalidada', NO_AUTORIZADO: 'No autorizado', SIN_EVALUACION: 'Sin evaluación',
  HERMETICO: 'Hermético', NO_HERMETICO: 'No hermético', INGRESO: 'Ingreso', SEGUIMIENTO: 'Seguimiento', CONTINUIDAD: 'Continuidad',
  GRANO: 'Grano', EXTERIOR: 'Exterior', ALMACEN: 'Almacén', LOTE: 'Lote',
  LIMPIEZA_GENERAL: 'Limpieza general', APERTURA: 'Apertura', RESELLADO: 'Resellado', SECADO: 'Secado', ENFRIAMIENTO: 'Enfriamiento', EXPOSICION_AGUA: 'Exposición al agua', CARGA_DESCARGA: 'Carga o descarga',
  CUARENTENA: 'Cuarentena', REVISION_PLAGAS: 'Revisión de plagas', REVISION_TERMICA: 'Revisión térmica', CORRECCION: 'Corrección',
  ABIERTA: 'Abierta', CERRADA: 'Cerrada', PENDIENTE: 'Pendiente', CONFIRMADA: 'Confirmada', DESCARTADA: 'Descartada',
  INSTRUMENTAL: 'Instrumental', LABORATORIO: 'Laboratorio', ESTIMACION_INDIRECTA: 'Estimación indirecta',
  PRODUCTOR: 'Productor', TECNICO: 'Técnico', ADMINISTRADOR: 'Administrador', INGENIERO_CONOCIMIENTO: 'Ingeniería del conocimiento',
  PUBLICADO: 'Publicado', MIXTO: 'Mixto', POLITICA_PROTOTIPO: 'Política del prototipo', TRANSFERIDO: 'Transferido',
  controles: 'Registrar control', eventos: 'Registrar evento', planes: 'Plan de monitoreo', dictamenes: 'Dictamen técnico',
  revisiones: 'Revisar incidencia', resoluciones: 'Resolver incidencia', admisiones: 'Registrar admisión',
}
export const nombre = (value: string) => ETIQUETAS[value] ?? value.toLowerCase().replaceAll('_', ' ').replace(/^./, c => c.toUpperCase())

export type Tono = 'ok' | 'warn' | 'crit' | 'info' | ''
/** Tono semántico de un estado o decisión para los badges. */
export function tonoEstado(valor: string | null | undefined): Tono {
  if (!valor) return ''
  if (valor === 'VIGENTE' || valor === 'CERRADA' || valor.startsWith('AUTORIZAR')) return 'ok'
  if (valor === 'ABIERTA' || valor === 'CORREGIR_Y_REEVALUAR' || valor === 'PENDIENTE') return 'warn'
  if (valor === 'SIN_EVALUACION' || valor === 'SIN_CONCLUSION_AUTOMATICA') return 'info'
  if (['VENCIDA', 'INVALIDADA', 'NO_AUTORIZADO', 'CUARENTENA', 'BLOQUEAR_INGRESO', 'RETIRAR_LOTE', 'CONFIRMADA'].includes(valor)) return 'crit'
  return ''
}
export const iniciales = (texto: string) => texto.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]!.toUpperCase()).join('') || '·'

// Etiquetas oficiales de las siete decisiones (Prompt 1). El código técnico se
// conserva en la API y en la explicación; al usuario se le muestra la etiqueta.
export const DECISIONES: Record<string, string> = {
  CUARENTENA: 'Separar y solicitar evaluación técnica',
  BLOQUEAR_INGRESO: 'Ingreso no autorizado',
  RETIRAR_LOTE: 'Suspender almacenamiento en las condiciones actuales',
  CORREGIR_Y_REEVALUAR: 'Corregir y volver a evaluar',
  SIN_CONCLUSION_AUTOMATICA: 'Faltan datos o revisión',
  AUTORIZAR_CON_MONITOREO: 'Almacenamiento autorizado con seguimiento reforzado',
  AUTORIZAR_ALMACENAMIENTO: 'Almacenamiento autorizado con controles ordinarios',
}
export const decision = (codigo: string) => DECISIONES[codigo] || nombre(codigo)
export const tonoDecision = (codigo: string) =>
  codigo === 'CUARENTENA' || codigo === 'BLOQUEAR_INGRESO' || codigo === 'RETIRAR_LOTE' ? 'danger'
    : codigo.startsWith('AUTORIZAR') ? 'authorized' : 'warning'
export const NOTA_PROTOTIPO = 'Prototipo académico. Evalúa condiciones de almacenamiento; no certifica inocuidad ni aptitud para consumo.'
export const tieneRol = (perfil: Schema['Perfil'] | undefined, rol: string) => !!perfil?.roles.includes(rol as never)
