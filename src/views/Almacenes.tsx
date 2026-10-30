import { useId, useState } from 'react'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, fecha, fechaRelativa, nombre, type Schema, type Unidad } from '../api/client'
import Panel, { Badge, Empty, ErrorMessage, Field, PageHeader, Skeleton, SkeletonPage } from '../components/Shared'
import InspeccionAlmacen from '../components/InspeccionAlmacen'
import EditarLote from '../components/EditarLote'
import { IconPackage, IconSearch } from '../components/Icons'
import { useAppNavigate } from '../App'

/** Almacenes y lotes: listado, búsqueda, filtros y detalle. */
export default function Almacenes() {
  const navigate = useAppNavigate()
  const perfil = useQueryClient().getQueryData<Schema['Perfil']>(['perfil'])
  const idBuscar = useId()
  const [q, setQ] = useState(''), [estado, setEstado] = useState(''), [modalidad, setModalidad] = useState(''), [seleccion, setSeleccion] = useState<string | null>(null)
  const data = useQuery({ queryKey: ['almacenes-lotes'], queryFn: async () => {
    const [almacenes, lotes, unidades] = await Promise.all([list<Schema['Almacen']>('/almacenes'), list<Schema['Lote']>('/lotes'), list<Unidad>('/unidades')])
    return { almacenes, lotes, unidades }
  } })
  const consultasVigencia = useQueries({queries:(data.data?.unidades ?? []).map(u=>({
    queryKey:['vigencia',u.id],queryFn:()=>request<Schema['Vigencia']>(`/unidades/${u.id}/vigencia`),staleTime:15000,
  }))})
  const vigencias = Object.fromEntries((data.data?.unidades ?? []).map((u,i)=>[u.id,consultasVigencia[i]?.data])) as Record<string,Schema['Vigencia']|undefined>
  const filas = (() => {
    if (!data.data) return []
    const d = data.data, texto = q.trim().toLowerCase()
    return d.unidades.map(u => ({ u, almacen: d.almacenes.find(a => a.id === u.id_almacen), lote: d.lotes.find(l => l.id === u.id_lote), vigencia: vigencias[u.id] }))
      .filter(f => !texto || [f.u.nombre_recipiente, f.almacen?.nombre, f.almacen?.ubicacion, f.lote?.codigo].some(v => v?.toLowerCase().includes(texto)))
      .filter(f => !estado || f.vigencia?.estado === estado)
      .filter(f => !modalidad || (modalidad === 'SIN' ? !f.u.tipo_almacenamiento : f.u.tipo_almacenamiento === modalidad))
  })()
  if (data.isLoading) return <SkeletonPage label="Cargando almacenes y lotes…" />
  if (!data.data) return <ErrorMessage error={data.error} onRetry={() => void data.refetch()} />
  const d = data.data
  const almacen = seleccion ? d.almacenes.find(a => a.id === seleccion) : null
  const estados = [...new Set(Object.values(vigencias).flatMap(v => v ? [v.estado] : []))]
  const filtrando = !!(q || estado || modalidad)
  const vigenciaBadge = (id: string) => vigencias[id] ? <Badge estado={vigencias[id]!.estado} /> : <Skeleton className="sk-pill" width={96} />

  return <div className="stack">
    <PageHeader eyebrow="Inventario" title="Almacenes y lotes" description={`${d.almacenes.length} almacenes · ${d.lotes.length} lotes · ${d.unidades.length} unidades`}
      actions={<button className="primary" onClick={() => navigate('dashboard')}>Registrar unidad</button>} />
    <ErrorMessage error={data.error} />
    <div className="filtros">
      <div className="field"><label htmlFor={idBuscar}>Buscar</label><div className="search-box"><IconSearch size={16} /><input id={idBuscar} type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Recipiente, almacén, ubicación o lote" /></div></div>
      <Field label="Autorización"><select value={estado} onChange={e => setEstado(e.target.value)}><option value="">Todas</option>{estados.map(s => <option key={s} value={s}>{nombre(s)}</option>)}</select></Field>
      <Field label="Modalidad"><select value={modalidad} onChange={e => setModalidad(e.target.value)}><option value="">Todas</option><option value="HERMETICO">Hermético</option><option value="NO_HERMETICO">No hermético</option><option value="SIN">Sin definir</option></select></Field>
      {filtrando && <button className="btn-ghost" onClick={() => { setQ(''); setEstado(''); setModalidad('') }}>Limpiar filtros</button>}
    </div>

    <Panel title="Almacenes">{d.almacenes.length ? <div className="table-scroll"><table className="table-cards"><thead><tr><th>Almacén</th><th>Ubicación</th><th>Clima cálido</th><th>Unidades</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>
      {d.almacenes.map(a => <tr key={a.id}><td data-label="Almacén"><strong>{a.nombre}</strong></td><td data-label="Ubicación">{a.ubicacion}</td><td data-label="Clima cálido">{a.clima_calido === null ? 'No se sabe' : a.clima_calido ? 'Sí' : 'No'}</td><td data-label="Unidades"><span className="badge">{d.unidades.filter(u => u.id_almacen === a.id).length}</span></td>
        <td data-label=""><div className="actions end"><button className={`btn-sm${seleccion === a.id ? ' primary' : ''}`} aria-expanded={seleccion === a.id} onClick={() => setSeleccion(seleccion === a.id ? null : a.id)}>{seleccion === a.id ? 'Ocultar detalle' : 'Ver detalle'}</button></div></td></tr>)}
    </tbody></table></div> : <Empty title="No hay almacenes registrados" icon={<IconPackage size={26} />}>Registra el primero desde Inicio para empezar.</Empty>}</Panel>

    {almacen && <Panel title={`Detalle · ${almacen.nombre}`}><InspeccionAlmacen key={almacen.id} id={almacen.id} revision={almacen.revision}/>
      <p>{almacen.ubicacion} · registrado {fecha(almacen.creado_en)}</p>
      <p>Clima cálido declarado: {almacen.clima_calido === null ? 'sin clasificar' : almacen.clima_calido ? 'sí' : 'no'}{almacen.fundamento_clima ? ` · Fundamento: ${almacen.fundamento_clima}` : ''}. Es contexto del almacén; el cálculo utiliza las mediciones de la matriz.</p>
      {d.unidades.filter(u => u.id_almacen === almacen.id).map(u => <div className="row" key={u.id}><span><strong>{u.nombre_recipiente}</strong><small>Lote {d.lotes.find(l => l.id === u.id_lote)?.codigo} · {u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Modalidad sin definir'}</small></span>{vigenciaBadge(u.id)}</div>)}
    </Panel>}

    <Panel title="Unidades por lote">{filas.length ? <div className="table-scroll"><table className="table-cards"><thead><tr><th>Lote</th><th>Recipiente</th><th>Almacén</th><th>Autorización</th><th>Próximo control</th><th><span className="sr-only">Acciones</span></th></tr></thead><tbody>
      {filas.map(({ u, almacen, lote, vigencia }) => <tr key={u.id}>
        <td data-label="Lote"><div><strong className="mono-cell">{lote?.codigo}</strong><small>Maíz chulpi · alimentación</small></div></td>
        <td data-label="Recipiente"><div>{u.nombre_recipiente}<small>{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Modalidad sin definir'}</small></div></td>
        <td data-label="Almacén">{almacen?.nombre}</td>
        <td data-label="Autorización">{vigenciaBadge(u.id)}</td>
        <td data-label="Próximo control">{vigencia ? <div><span>{fechaRelativa(vigencia.fecha_proximo_control ?? null)}</span>{vigencia.fecha_proximo_control && <small>{fecha(vigencia.fecha_proximo_control)}</small>}</div> : <Skeleton className="sk-line" width={90} />}</td>
        <td data-label=""><div className="actions end"><button className="primary btn-sm" onClick={() => navigate('evaluacion', u.id)}>Evaluar</button><button className="btn-sm" onClick={() => navigate('seguimiento', u.id)}>Seguimiento</button>{u.id_evaluacion_actual && <button className="btn-ghost btn-sm" onClick={() => navigate('resultado', u.id_evaluacion_actual!)}>Resultado</button>}</div></td></tr>)}
    </tbody></table></div> : <Empty title={filtrando ? 'Sin coincidencias' : 'Aún no hay unidades'} icon={<IconSearch size={26} />} action={filtrando && <button onClick={() => { setQ(''); setEstado(''); setModalidad('') }}>Limpiar filtros</button>}>{filtrando ? 'Ninguna unidad coincide con los filtros.' : 'Crea una unidad desde Inicio para evaluarla.'}</Empty>}</Panel>

    <Panel title="Lotes">{d.lotes.length ? d.lotes.map(l => <div className="row" key={l.id}><span><strong className="mono-cell">{l.codigo}</strong><small>Registrado {fecha(l.creado_en)}</small></span><div className="actions"><span className="badge">{d.unidades.filter(u => u.id_lote === l.id).length} unidades</span>{l.id_propietario === perfil?.id && <EditarLote key={`${l.id}:${l.revision}`} lote={l} />}</div></div>) : <Empty>No hay lotes registrados.</Empty>}</Panel>
  </div>
}
