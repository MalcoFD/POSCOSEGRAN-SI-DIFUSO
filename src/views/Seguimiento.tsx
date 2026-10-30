import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, write, revisiones, fecha, fechaRelativa, nombre, decision, tonoEstado, type Schema, type Unidad, type Resultado } from '../api/client'
import Panel, { Badge, Empty, ErrorMessage, Field, PageHeader, Skeleton, SkeletonPage } from '../components/Shared'
import { useToast } from '../components/Toast'
import { IconActivity } from '../components/Icons'
import Captura, { ahoraLocal, convertir, type CapturaDatos } from '../components/Captura'
import InspeccionMatricial from '../components/InspeccionMatricial'
import { useAppNavigate, useId } from '../App'

const opciones = (valores: string[]) => valores.map(t => <option key={t} value={t}>{nombre(t)}</option>)
const colorTono: Record<string, string> = { ok: 'var(--color-ok)', warn: 'var(--color-warn)', crit: 'var(--color-crit)', info: 'var(--color-infoblue)', '': '#8C7B5C' }

export default function Seguimiento() {
  const id = useId(), navigate = useAppNavigate()
  const unidades = useQuery({ queryKey: ['unidades'], queryFn: () => list<Unidad>('/unidades'), enabled: !id })
  if (!id) return <div className="stack">
    <PageHeader eyebrow="Historial y actuaciones" title="Seguimiento" description="Elige una unidad para ver su historial, controles e incidencias." />
    <ErrorMessage error={unidades.error} onRetry={() => void unidades.refetch()} />
    {unidades.isLoading ? <div className="unit-picker" aria-busy="true">{[0, 1, 2].map(i => <div className="unit-card" key={i} aria-hidden="true"><Skeleton className="sk-line" width="60%" height={14} /><Skeleton className="sk-btn" width={110} height={36} /></div>)}<span className="sr-only">Cargando unidades…</span></div>
      : unidades.data?.length ? <div className="unit-picker">{unidades.data.map(u => <article className="unit-card" key={u.id}><header><div><strong>{u.nombre_recipiente}</strong><small>{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Modalidad sin definir'}</small></div></header><div className="actions"><button className="primary btn-sm" onClick={() => navigate('seguimiento', u.id)}>Ver seguimiento</button></div></article>)}</div>
      : <Empty title="No hay unidades registradas" icon={<IconActivity size={26} />}>Crea una unidad desde Inicio para registrar su seguimiento.</Empty>}
  </div>
  return <Detalle key={id} id={id} />
}

type Pestana = 'incidencias' | 'evaluaciones' | 'controles' | 'planes' | 'eventos'

function Detalle({ id }: { id: string }) {
  const navigate = useAppNavigate(), qc = useQueryClient(), avisar = useToast()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const [action, setAction] = useState(''), [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false), [message, setMessage] = useState('')
  const [pestana, setPestana] = useState<Pestana | null>(null)
  const [datos, setDatos] = useState<CapturaDatos>({})
  const [form, setForm] = useState({ tipoControl: 'GRANO', tipoEvento: 'APERTURA', fecha: ahoraLocal(), evidencia: '', proximo: '', salida: '', intervalo: '', actividades: '', humedadMin: '', humedadMax: '', plazo: '', vence: '', condiciones: '', incidencia: '', resultado: 'PENDIENTE', disposicion: '', tipoAdmision: 'INGRESO' })
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  const storageKey = `seguimiento:${perfil?.id}:${id}`
  const [restored, setRestored] = useState(false)
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
      if (saved) { setForm(saved.form); setDatos(saved.datos); setAction(saved.action) }
    } catch { /* Una captura local corrupta no impide consultar el historial. */ }
    setRestored(true)
  }, [storageKey])
  useEffect(() => { if (restored) sessionStorage.setItem(storageKey, JSON.stringify({ form, datos, action })) }, [storageKey, restored, form, datos, action])
  const data = useQuery({ queryKey: ['seguimiento', id], queryFn: async () => {
    const [u, historial, controles, planes, dictamenes, incidencias, eventos, vigencia] = await Promise.all([
      request<Unidad>(`/unidades/${id}`), list<Resultado>(`/unidades/${id}/historial`), list<Schema['Control']>(`/unidades/${id}/controles`), list<Schema['Plan']>(`/unidades/${id}/planes`), list<Schema['Dictamen']>(`/unidades/${id}/dictamenes`), list<Schema['Incidencia']>(`/unidades/${id}/incidencias`), list<{id: string; tipo: string; fecha: string; evidencia: string}>(`/unidades/${id}/eventos`), request<Schema['Vigencia']>(`/unidades/${id}/vigencia`),
    ])
    return { u, historial, controles, planes, dictamenes, incidencias, eventos, vigencia }
  } })
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setMessage('')
    try {
      if (!data.data) throw new Error('Espera a que cargue la unidad')
      const revisions = revisiones(data.data.u)
      let path = `/unidades/${id}/${action}`, body: unknown
      if (action === 'controles') body = { ...revisions, tipo: form.tipoControl, fecha: new Date(form.fecha).toISOString(), evidencia: form.evidencia, observaciones: convertir(Object.fromEntries(Object.entries(datos).filter(([k]) => (form.tipoControl === 'ALMACEN' ? ['hr_almacen'] : form.tipoControl === 'EXTERIOR' ? ['estado_barrera'] : ['humedad_grano','temperatura_grano','hr_almacen','estado_fisico_sanitario','estado_barrera','procedimiento_interno']).includes(k)))) }
      else if (action === 'eventos') body = { ...revisions, tipo: form.tipoEvento, fecha: new Date(form.fecha).toISOString(), evidencia: form.evidencia }
      else if (action === 'planes') body = { ...revisions, fecha_proximo_control: new Date(form.proximo).toISOString(), fecha_salida_prevista: new Date(form.salida).toISOString(), intervalo_dias: Number(form.intervalo), actividades: form.actividades }
      else if (action === 'dictamenes') body = { ...revisions, humedad_min: Number(form.humedadMin.replace(',', '.')), humedad_max: Number(form.humedadMax.replace(',', '.')), plazo_maximo_dias: Number(form.plazo), vence_en: new Date(form.vence).toISOString(), condiciones: form.condiciones, evidencia: form.evidencia }
      else if (action === 'admisiones') body = { ...revisions, id_evaluacion: data.data.u.id_evaluacion_actual, tipo: form.tipoAdmision }
      else {
        const incidencia = data.data.incidencias.find(i => i.id === form.incidencia)
        if (!incidencia) throw new Error('Selecciona una incidencia')
        path = `/incidencias/${incidencia.id}/${action}`
        body = { ...revisions, revision_incidencia: incidencia.revision, evidencia: form.evidencia, ...(action === 'revisiones' ? { resultado: form.resultado } : { disposicion: form.disposicion }) }
      }
      const result = await write<{completo?: boolean; campos_pendientes?: string[]}>(path, body)
      setMessage(action === 'controles' ? (result.completo ? 'Control completo registrado. Reevalúa la unidad.' : `Control parcial registrado. Pendientes: ${result.campos_pendientes?.map(nombre).join(', ')}. Reevalúa para obtener la decisión.`) : action === 'admisiones' ? 'Admisión registrada con autorización vigente.' : 'Registro guardado. Reevalúa la unidad para conocer su nueva decisión.')
      avisar('Actuación guardada', 'Reevalúa la unidad para conocer su nueva decisión.')
      await Promise.all([['seguimiento', id], ['unidad', id], ['vigencia', id], ['inicio'], ['revision-tecnica']].map(queryKey => qc.invalidateQueries({ queryKey })))
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  if (data.isLoading) return <SkeletonPage label="Cargando el seguimiento…" />
  if (!data.data) return <ErrorMessage error={data.error} onRetry={() => void data.refetch()} />
  const d = data.data, tecnico = perfil?.roles.includes('TECNICO')
  const abiertas = d.incidencias.filter(i => i.estado === 'ABIERTA').length
  const activa: Pestana = pestana ?? (abiertas ? 'incidencias' : 'evaluaciones')
  const ultima = d.historial[0]?.evaluacion
  const pestanas: [Pestana, string, number][] = [['incidencias', 'Incidencias', d.incidencias.length], ['evaluaciones', 'Evaluaciones', d.historial.length], ['controles', 'Controles', d.controles.length], ['planes', 'Planes', d.planes.length], ['eventos', 'Eventos', d.eventos.length]]
  return <div className="stack">
    <PageHeader back={{ label: 'Volver al inicio', onClick: () => navigate('dashboard') }} eyebrow="Historial y actuaciones" title="Seguimiento"
      description={<>{d.u.nombre_recipiente} · <Badge estado={d.vigencia.estado} /></>}
      actions={<><button onClick={() => void data.refetch()}>{data.isFetching ? 'Actualizando…' : 'Actualizar datos'}</button><button className="primary" onClick={() => navigate('evaluacion', id)}>Reevaluar unidad</button></>} />
    <div className="metrics">
      <div className="panel"><span>Última decisión</span><strong style={{ fontSize: 16 }}>{ultima ? decision(ultima.decision_final) : 'Sin evaluaciones'}</strong></div>
      <div className="panel"><span>Próximo control</span><strong style={{ fontSize: 16 }}>{fechaRelativa(d.vigencia.fecha_proximo_control ?? null)}</strong></div>
      <div className={`panel${abiertas ? ' metric-card warn' : ''}`}><div><span>Incidencias abiertas</span><strong style={{ fontSize: 16 }}>{abiertas}</strong></div></div>
    </div>
    <ErrorMessage error={error || data.error} />{message && <p className="message ok" role="status">{message}</p>}
    <div className="actions" role="group" aria-label="Registrar una actuación">{[['controles','Registrar control'],['eventos','Registrar evento'],['planes','Plan de monitoreo'],...(tecnico ? [['revisiones','Revisar incidencia'],['resoluciones','Resolver incidencia']] : []),['admisiones','Registrar admisión']].map(([k,label]) => <button key={k} className={`btn-sm${action === k ? ' primary' : ''}`} aria-pressed={action === k} onClick={() => setAction(action === k ? '' : k)}>{label}</button>)}</div>
    {action && <Panel title={nombre(action)}><form className="stack compact" style={{ marginTop: 0 }} onSubmit={e => void submit(e)}><div className="form-grid" style={{ marginTop: 0 }}>
      {action === 'controles' && <Field label="Tipo de control"><select value={form.tipoControl} onChange={e => set('tipoControl',e.target.value)}>{opciones(['INGRESO','GRANO','EXTERIOR','ALMACEN'])}</select></Field>}
      {action === 'eventos' && <Field label="Tipo de evento"><select value={form.tipoEvento} onChange={e => set('tipoEvento',e.target.value)}>{opciones(['LIMPIEZA_GENERAL','APERTURA','RESELLADO','SECADO','ENFRIAMIENTO','EXPOSICION_AGUA','CARGA_DESCARGA'])}</select></Field>}
      {['controles','eventos'].includes(action) && <Field label="Fecha de la actuación"><input required type="datetime-local" value={form.fecha} onChange={e => set('fecha', e.target.value)} /></Field>}
      {['controles','eventos','dictamenes','revisiones','resoluciones'].includes(action) && <Field label="Evidencia de la actuación"><textarea required value={form.evidencia} onChange={e => set('evidencia',e.target.value)} /></Field>}
      {action === 'planes' && <><Field label="Fecha del próximo control"><input required type="datetime-local" value={form.proximo} onChange={e => set('proximo',e.target.value)} /></Field><Field label="Fecha de salida prevista"><input required type="datetime-local" value={form.salida} onChange={e => set('salida',e.target.value)} /></Field><Field label="Intervalo entre controles (días)"><input required type="number" min="1" max="365" value={form.intervalo} onChange={e => set('intervalo',e.target.value)} /></Field><Field label="Actividades de monitoreo"><textarea required value={form.actividades} onChange={e => set('actividades',e.target.value)} /></Field></>}
      {['revisiones','resoluciones'].includes(action) && <><Field label="Incidencia abierta"><select required value={form.incidencia} onChange={e => set('incidencia', e.target.value)}><option value="">Seleccionar</option>{d.incidencias.filter(i => i.estado === 'ABIERTA').map(i => <option key={i.id} value={i.id}>{nombre(i.tipo)} · {fecha(i.creada_en)}</option>)}</select></Field>{action === 'revisiones' ? <Field label="Resultado de la revisión"><select value={form.resultado} onChange={e => set('resultado',e.target.value)}>{opciones(['PENDIENTE','CONFIRMADA','DESCARTADA'])}</select></Field> : <Field label="Disposición y fundamento del cierre"><textarea required value={form.disposicion} onChange={e => set('disposicion',e.target.value)} /></Field>}</>}
      {action === 'admisiones' && <><Field label="Tipo de admisión" hint="El servidor comprobará nuevamente la vigencia antes de registrar la admisión."><select value={form.tipoAdmision} onChange={e => set('tipoAdmision',e.target.value)}>{opciones(['INGRESO','CONTINUIDAD'])}</select></Field>{d.vigencia.estado !== 'VIGENTE' && <p className="message" style={{ margin: 0 }}>La admisión requiere una autorización vigente.</p>}</>}
    </div>{action === 'controles' && <><p className="muted">Registra los campos inspeccionados. El control registra observaciones; la recomendación se obtiene al reevaluar con la matriz. En hermético, usa el control exterior sin abrir rutinariamente.</p><Captura datos={datos} onChange={setDatos} filtro={form.tipoControl === 'ALMACEN' ? ['hr_almacen'] : form.tipoControl === 'EXTERIOR' ? [] : ['humedad_grano','temperatura_grano', ...(d.u.tipo_almacenamiento === 'HERMETICO' ? [] : ['hr_almacen'])]} />{form.tipoControl !== 'ALMACEN' && <InspeccionMatricial datos={datos} historicos={{}} onChange={setDatos} hermetico={d.u.tipo_almacenamiento === 'HERMETICO'} />}</>}
    <div className="actions"><button className="primary" disabled={busy || (action === 'admisiones' && d.vigencia.estado !== 'VIGENTE')}>{busy ? 'Guardando…' : 'Guardar actuación'}</button><button type="button" onClick={() => setAction('')}>Cancelar</button></div></form></Panel>}

    <section className="panel" style={{ padding: 0 }}>
      <div className="tabs" role="tablist" aria-label="Registros de la unidad">{pestanas.map(([k, label, n]) => <button key={k} role="tab" id={`tab-${k}`} aria-controls={`panel-${k}`} aria-selected={activa === k} tabIndex={activa === k ? 0 : -1} onClick={() => setPestana(k)}
        onKeyDown={e => { if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return; const i = pestanas.findIndex(p => p[0] === activa); const sig = pestanas[(i + (e.key === 'ArrowRight' ? 1 : pestanas.length - 1)) % pestanas.length][0]; setPestana(sig); document.getElementById(`tab-${sig}`)?.focus() }}>
        {label} <span className="tab-count">{n}</span></button>)}</div>
      <div role="tabpanel" id={`panel-${activa}`} aria-labelledby={`tab-${activa}`} style={{ padding: 24 }}>
        {activa === 'incidencias' && (d.incidencias.length ? d.incidencias.map(i => <div key={i.id} className="reason"><div className="actions"><Badge estado={i.tipo} tono={i.estado === 'ABIERTA' ? 'warn' : 'ok'}>{nombre(i.tipo)}</Badge><Badge estado={i.estado} /></div><p>{i.causas.map(nombre).join(', ') || 'Sin detalle'} · {fecha(i.creada_en)}</p><IncidenciaHistorial id={i.id} /></div>) : <Empty>No hay incidencias registradas.</Empty>)}
        {activa === 'evaluaciones' && (d.historial.length ? <ol className="timeline">{d.historial.map(r => <li key={r.evaluacion.id} style={{ color: colorTono[tonoEstado(r.evaluacion.decision_final)] }}>
          <div className="rail" aria-hidden="true"><span /><span /></div>
          <div className="card" style={{ color: 'var(--color-text)' }}><div><strong style={{ color: 'var(--color-forest)' }}>{decision(r.evaluacion.decision_final)}</strong><small>{fecha(r.evaluacion.fecha_evaluacion)} · {nombre(r.vigencia.estado)}</small></div><button className="btn-sm" onClick={() => navigate('resultado',r.evaluacion.id)}>Ver explicación</button></div>
        </li>)}</ol> : <Empty>No hay evaluaciones registradas.</Empty>)}
        {activa === 'controles' && (d.controles.length ? d.controles.map(c => <div className="row" key={c.id}><div><strong>{nombre(c.tipo)} · {fecha(c.fecha)}</strong><small>{c.completo ? 'Completo' : `Parcial: ${c.campos_pendientes.map(nombre).join(', ')}`}</small></div><p className="muted" style={{ margin: 0 }}>{c.evidencia}</p></div>) : <Empty>No hay controles.</Empty>)}
        {activa === 'planes' && (d.planes.length ? d.planes.map(p => <div className="row" key={p.id}><div><strong>{p.actividades}</strong><small>Cada {p.intervalo_dias} días · control {fecha(p.fecha_proximo_control)}</small></div><Badge tono={p.vigente ? 'ok' : ''}>{p.vigente ? 'Activo' : 'Sustituido'}</Badge></div>) : <Empty>No hay planes.</Empty>)}
        {activa === 'eventos' && (d.eventos.length ? d.eventos.map(e => <div className="row" key={e.id}><div><strong>{nombre(e.tipo)}</strong><small>{fecha(e.fecha)}</small></div><p className="muted" style={{ margin: 0 }}>{e.evidencia}</p></div>) : <Empty>No hay eventos.</Empty>)}
      </div>
    </section>
  </div>
}

function IncidenciaHistorial({ id }: { id: string }) {
  const [open,setOpen] = useState(false)
  const data = useQuery({ queryKey:['incidencia-historial',id], enabled:open, queryFn:async () => ({ revisiones:await list<Schema['Revision']>(`/incidencias/${id}/revisiones`), resoluciones:await list<Schema['Resolucion']>(`/incidencias/${id}/resoluciones`) }) })
  return <details onToggle={e => setOpen(e.currentTarget.open)}><summary>Revisiones y resoluciones</summary><ErrorMessage error={data.error}/>{data.isLoading && <Skeleton className="sk-line" width="60%" />}{data.data?.revisiones.map(r => <p key={r.id}>{fecha(r.fecha)} · {nombre(r.resultado)} · {r.evidencia}</p>)}{data.data?.resoluciones.map(r => <p key={r.id}>{fecha(r.fecha)} · {r.disposicion} · {r.evidencia}</p>)}{data.data && !data.data.revisiones.length && !data.data.resoluciones.length && <p className="muted">Sin revisiones todavía.</p>}</details>
}
