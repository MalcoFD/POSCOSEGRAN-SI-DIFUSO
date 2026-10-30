import { useState } from 'react'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, write, nombre, fecha, fechaRelativa, type Schema, type Unidad } from '../api/client'
import Panel, { Badge, Empty, ErrorMessage, Field, PageHeader, Skeleton, SkeletonPage } from '../components/Shared'
import { useToast } from '../components/Toast'
import { IconCalendar, IconCheck, IconPackage, IconPlus, IconShieldAlert, IconWrench, IconX } from '../components/Icons'
import { useAppNavigate } from '../App'

export default function Dashboard() {
  const navigate = useAppNavigate(), qc = useQueryClient(), avisar = useToast()
  const [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false), [show, setShow] = useState(false)
  const data = useQuery({ queryKey: ['inicio'], queryFn: async () => {
    const [inicio, almacenes, lotes, unidades, perfil] = await Promise.all([
      request<Schema['Inicio']>('/inicio'), list<Schema['Almacen']>('/almacenes'), list<Schema['Lote']>('/lotes'), list<Unidad>('/unidades'), request<Schema['Perfil']>('/me'),
    ])
    return { inicio, almacenes, lotes, unidades, perfil }
  } })
  const vigencias = useQueries({queries:(data.data?.unidades ?? []).map(u=>({
    queryKey:['vigencia',u.id],queryFn:()=>request<Schema['Vigencia']>(`/unidades/${u.id}/vigencia`),staleTime:15000,
  }))})
  const [form, setForm] = useState({ nombre: '', ubicacion: '', clima: '', fundamento: '', codigo: '', almacen: '', lote: '', recipiente: '', modalidad: '' })
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  async function save(e: React.FormEvent, kind: 'almacenes' | 'lotes' | 'unidades') {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      const body = kind === 'almacenes' ? { nombre: form.nombre, ubicacion: form.ubicacion, clima_calido: form.clima === '' ? null : form.clima === 'si', fundamento_clima: form.fundamento || null }
        : kind === 'lotes' ? { codigo: form.codigo, variedad: 'MAIZ_CHULPI', uso_final: 'ALIMENTACION' }
        : { id_lote: form.lote, id_almacen: form.almacen, nombre_recipiente: form.recipiente, tipo_almacenamiento: form.modalidad || null }
      const created = await write<{ id: string }>(`/${kind}`, body)
      if (kind === 'almacenes') { set('almacen', created.id); avisar('Almacén guardado', 'Ahora registra el lote de maíz chulpi.') }
      if (kind === 'lotes') { set('lote', created.id); avisar('Lote guardado', 'Completa el recipiente para crear la unidad.') }
      await Promise.all([qc.invalidateQueries({ queryKey: ['inicio'] }), qc.invalidateQueries({ queryKey: ['almacenes-lotes'] }), qc.invalidateQueries({ queryKey: ['unidades'] })])
      if (kind === 'unidades') { avisar('Unidad creada', 'Empieza la captura guiada.'); navigate('evaluacion', created.id) }
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  if (data.isLoading) return <SkeletonPage metrics label="Cargando inicio…" />
  if (!data.data) return <ErrorMessage error={data.error} onRetry={() => void data.refetch()} />
  const d = data.data
  const productor = d.perfil.roles.includes('PRODUCTOR')
  if (!d.perfil.roles.some(r=>r==='PRODUCTOR'||r==='TECNICO')) {
    const admin = d.perfil.roles.includes('ADMINISTRADOR')
    return <div className="stack"><PageHeader eyebrow={admin ? 'Administración' : 'Ingeniería del conocimiento'} title="Inicio" description={`Hola, ${d.perfil.nombre}.`} />
      <Panel title={admin?'Administración de accesos':'Ingeniería del conocimiento Mamdani'}><p>{admin?'Coordina las asignaciones de técnicos sin acceder al detalle de las evaluaciones de producción.':'Revisa las funciones de pertenencia, las reglas finales y el impacto antes de activar una nueva versión. La evaluación final procede del centroide Mamdani.'}</p>
        <div className="actions" style={{ marginTop: 16 }}><button className="primary" onClick={()=>navigate(admin?'configuracion':'adquisicion')}>{admin?'Gestionar asignaciones':'Mantener modelo Mamdani'}</button><button onClick={()=>navigate('conocimiento')}>Revisar conocimiento y fuentes</button></div></Panel></div>
  }
  const pasos = [
    { titulo: 'Almacén', listo: !!form.almacen, detalle: d.almacenes.find(a => a.id === form.almacen)?.nombre },
    ...(productor ? [{ titulo: 'Lote de maíz chulpi', listo: !!form.lote, detalle: d.lotes.find(l => l.id === form.lote)?.codigo }] : []),
    { titulo: 'Unidad de almacenamiento', listo: false, detalle: undefined },
  ]
  const actual = pasos.findIndex(p => !p.listo)
  return <div className="stack">
    <PageHeader eyebrow="Control del almacenamiento" title="Inicio" description="Tus unidades, sus condiciones y el próximo paso."
      actions={<button className="primary" onClick={() => setShow(!show)} aria-expanded={show}>{show ? <><IconX size={16} strokeWidth={2.4} />Cerrar registro</> : <><IconPlus size={16} strokeWidth={2.4} />Registrar unidad</>}</button>} />
    <div className="metrics">
      <div className="panel metric-card"><div className="metric-icon"><IconPackage size={22} /></div><div><span>Unidades registradas</span><strong>{d.inicio.unidades_total}</strong></div></div>
      <div className={`panel metric-card${d.inicio.cuarentenas_abiertas ? ' crit' : ''}`}><div className={`metric-icon${d.inicio.cuarentenas_abiertas ? ' crit' : ''}`}><IconShieldAlert size={22} /></div><div><span>Cuarentenas abiertas</span><strong>{d.inicio.cuarentenas_abiertas}</strong></div></div>
      <div className={`panel metric-card${d.inicio.correcciones_pendientes ? ' warn' : ''}`}><div className={`metric-icon${d.inicio.correcciones_pendientes ? ' warn' : ''}`}><IconWrench size={22} /></div><div><span>Correcciones pendientes</span><strong>{d.inicio.correcciones_pendientes}</strong></div></div>
    </div>
    <ErrorMessage error={error || data.error} />
    {show && <Panel title="Registrar almacén, lote y unidad">
      <ol className="wizard-steps" aria-label="Pasos del registro">{pasos.map((p, i) => <li key={p.titulo} className={p.listo ? 'done' : i === actual ? 'current' : ''} aria-current={i === actual ? 'step' : undefined}>
        <span className="step-mark">{p.listo ? <IconCheck size={13} strokeWidth={3} /> : i + 1}</span>
        <span><strong>{p.titulo}</strong>{p.listo ? `${p.detalle ?? 'Seleccionado'} · listo` : i === actual ? 'Paso actual' : 'Pendiente'}</span>
      </li>)}</ol>
      <p className="muted" style={{ margin: '16px 0 0' }}>Cada unidad representa condiciones homogéneas. Puedes usar un almacén o lote ya registrado desde el último paso.</p>
      <div className="form-grid">
        <form className="stack compact" onSubmit={e => void save(e, 'almacenes')}><h3>1. Almacén</h3>
          <Field label="Nombre del almacén"><input required value={form.nombre} onChange={e => set('nombre', e.target.value)} /></Field>
          <Field label="Ubicación"><input required value={form.ubicacion} onChange={e => set('ubicacion', e.target.value)} /></Field>
          <Field label="Clima cálido documentado"><select value={form.clima} onChange={e => set('clima', e.target.value)}><option value="">No se sabe</option><option value="si">Sí</option><option value="no">No</option></select></Field>
          <Field label="Fundamento del clima" hint={form.clima !== '' ? 'Obligatorio si indicas el clima.' : undefined}><input required={form.clima !== ''} value={form.fundamento} onChange={e => set('fundamento', e.target.value)} /></Field>
          <button disabled={busy}>Guardar almacén</button></form>
        {productor && <form className="stack compact" onSubmit={e => void save(e, 'lotes')}><h3>2. Lote de maíz chulpi</h3>
          <Field label="Código del lote"><input required value={form.codigo} onChange={e => set('codigo', e.target.value)} /></Field><p className="muted" style={{ margin: 0, fontSize: 14 }}>Uso final: alimentación.</p><button disabled={busy}>Guardar lote</button></form>}
        <form className="stack compact" onSubmit={e => void save(e, 'unidades')}><h3>{productor ? 3 : 2}. Unidad de almacenamiento</h3>
          <Field label="Almacén"><select required value={form.almacen} onChange={e => set('almacen', e.target.value)}><option value="">Seleccionar</option>{d.almacenes.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></Field>
          <Field label="Lote"><select required value={form.lote} onChange={e => set('lote', e.target.value)}><option value="">Seleccionar</option>{d.lotes.map(a => <option key={a.id} value={a.id}>{a.codigo}</option>)}</select></Field>
          <Field label="Nombre del recipiente"><input required value={form.recipiente} onChange={e => set('recipiente', e.target.value)} /></Field>
          <Field label="Modalidad"><select value={form.modalidad} onChange={e => set('modalidad', e.target.value)}><option value="">No se sabe</option><option value="HERMETICO">Hermético</option><option value="NO_HERMETICO">No hermético</option></select></Field>
          <button className="primary" disabled={busy}>Crear unidad y capturar</button></form>
      </div></Panel>}
    <Panel title="Unidades de almacenamiento">{!d.unidades.length
      ? <Empty title="Aún no tienes unidades" icon={<IconPackage size={26} />} action={!show && <button className="primary" onClick={() => setShow(true)}>Registrar la primera unidad</button>}>Registra un almacén, un lote y su recipiente para hacer la primera evaluación.</Empty>
      : <div className="table-scroll"><table className="table-cards"><thead><tr><th>Recipiente</th><th>Modalidad</th><th>Autorización actual</th><th>Próximo control</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>{d.unidades.map((u, i) => {const v=vigencias[i];return <tr key={u.id}>
        <td data-label="Recipiente"><div><strong>{u.nombre_recipiente}</strong><small>Lote {d.lotes.find(l => l.id === u.id_lote)?.codigo}</small></div></td>
        <td data-label="Modalidad">{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Sin definir'}</td>
        <td data-label="Autorización">{v?.data ? <Badge estado={v.data.estado} /> : v?.error ? <Badge tono="">No disponible</Badge> : <Skeleton className="sk-pill" width={96} />}</td>
        <td data-label="Próximo control">{v?.isLoading ? <Skeleton className="sk-line" width={90} /> : <div><span>{fechaRelativa(v?.data?.fecha_proximo_control ?? null)}</span>{v?.data?.fecha_proximo_control && <small>{fecha(v.data.fecha_proximo_control)}</small>}</div>}</td>
        <td data-label=""><div className="actions end"><button className="primary btn-sm" onClick={() => navigate('evaluacion', u.id)}>Evaluar</button><button className="btn-sm" onClick={() => navigate('seguimiento', u.id)}>Seguimiento</button>{u.id_evaluacion_actual && <button className="btn-ghost btn-sm" onClick={() => navigate('resultado', u.id_evaluacion_actual!)}>Resultado</button>}</div></td>
      </tr>})}</tbody></table></div>}</Panel>
    <Panel title="Controles próximos">{d.inicio.controles_proximos.length ? d.inicio.controles_proximos.map(c => <div key={c.id_unidad} className="row">
      <div className="list-item"><div className={`list-icon${new Date(c.fecha).getTime() - Date.now() < 2 * 86_400_000 ? ' warn' : ''}`}><IconCalendar size={20} /></div><div><strong>{c.nombre}</strong><span className="muted" style={{ fontSize: 13 }}>{fechaRelativa(c.fecha)} · {fecha(c.fecha)} · {nombre(c.estado)}</span></div></div>
      <button className="btn-sm" onClick={() => navigate('seguimiento', c.id_unidad)}>Registrar control</button></div>) : <Empty>No hay controles programados.</Empty>}</Panel>
  </div>
}
