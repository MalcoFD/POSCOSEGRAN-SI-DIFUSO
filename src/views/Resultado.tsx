import { useQuery } from '@tanstack/react-query'
import { ApiError, request, fecha, fechaRelativa, nombre, decision, tonoDecision, type Resultado as ResultadoAPI, type Schema } from '../api/client'
import Panel, { Badge, Empty, ErrorMessage, PageHeader, SkeletonPage } from '../components/Shared'
import { IconCheck, IconHelp, IconShieldAlert, IconShieldCheck } from '../components/Icons'
import { etiqueta } from '../components/Captura'
import InferenciaDifusa from '../components/InferenciaDifusa'
import { useAppNavigate, useId } from '../App'

type Explicacion = Schema['Explicacion']

export default function Resultado() {
  const id = useId(), navigate = useAppNavigate()
  const result = useQuery({ queryKey: ['resultado', id], queryFn: () => request<ResultadoAPI>(`/evaluaciones/${id}`), enabled: !!id, refetchInterval: 30000 })
  const explicacion = useQuery({ queryKey: ['explicacion', id], queryFn: () => request<Explicacion>(`/evaluaciones/${id}/explicacion`), enabled: !!id, staleTime: Infinity })
  const catalogo = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  if (!id) return <div className="stack"><PageHeader title="Resultado de evaluación" /><Panel><Empty title="Ninguna evaluación seleccionada" icon={<IconHelp size={26} />} action={<button className="primary" onClick={() => navigate('dashboard')}>Ir a Inicio</button>}>Selecciona una evaluación desde Inicio o Seguimiento.</Empty></Panel></div>
  if (result.isLoading) return <SkeletonPage label="Cargando el resultado…" />
  if (!result.data) return <ErrorMessage error={result.error} onRetry={() => void result.refetch()} />
  const { evaluacion: e, vigencia: v } = result.data
  const x = explicacion.data
  const pendientesPorPaso = [...e.datos_pendientes].sort((a, b) => a.paso - b.paso)
  const tono = tonoDecision(e.decision_final)
  const Icono = tono === 'danger' ? IconShieldAlert : tono === 'authorized' ? IconShieldCheck : IconHelp

  return <div className="stack">
    <PageHeader back={{ label: 'Volver al seguimiento', onClick: () => navigate('seguimiento', e.id_unidad) }} eyebrow="Decisión explicable · Mamdani" title="Resultado de evaluación"
      description={`Evaluado ${fechaRelativa(e.fecha_evaluacion).toLowerCase()} · ${fecha(e.fecha_evaluacion)}`}
      actions={<><button onClick={() => navigate('seguimiento', e.id_unidad)}>Ver seguimiento</button><button className="primary" onClick={() => navigate('evaluacion', e.id_unidad)}>Reevaluar unidad</button></>} />
    <ErrorMessage error={result.error} />

    {/* 1. Qué hacer */}
    <section className={`decision ${tono}`} aria-labelledby="que-hacer">
      <div className="decision-icon" aria-hidden="true"><Icono size={28} strokeWidth={2} /></div>
      <div className="decision-body">
        <p id="que-hacer" className="eyebrow" style={{ color: 'inherit' }}>Qué hacer</p>
        <h2>{decision(e.decision_final)}</h2>
        <p>Autorización actual: <Badge estado={v.estado} /></p>
        {v.causas.map(c => <p key={c} className="muted">{c}</p>)}
        <div className="actions" style={{ marginTop: 8 }}><button className="btn-sm" onClick={() => void result.refetch()}>{result.isFetching ? 'Consultando…' : 'Consultar vigencia'}</button></div>
      </div>
    </section>

    <InferenciaDifusa informe={e.difuso} />

    <div className="fuzzy-grid">
      {/* 2. Por qué */}
      <Panel title="Por qué">
        {x ? <p>{x.resumen}</p> : explicacion.isLoading ? <p className="muted">Preparando la explicación…</p> : null}
        {explicacion.error instanceof ApiError && explicacion.error.status === 409 && <p className="muted">Esta evaluación se emitió antes de que el sistema guardara su traza: se muestran solo sus motivos.</p>}
        {e.motivos.slice(0, 4).map(m => <p key={m.id} className="row" style={{ justifyContent: 'flex-start', flexWrap: 'nowrap' }}><span className="badge code">{m.regla}</span> <span>{m.mensaje}</span></p>)}
        {e.motivos.length > 4 && <p className="muted">Y {e.motivos.length - 4} motivos más en el fundamento técnico.</p>}
      </Panel>

      {/* 3. Acciones */}
      <Panel title="Acciones requeridas">{e.acciones_requeridas.length ? e.acciones_requeridas.map((a, i) => <div className="row" key={i} style={{ justifyContent: 'flex-start', flexWrap: 'nowrap' }}><span className="step-mark" aria-hidden="true" style={{ borderRadius: 6 }} /><p style={{ margin: 0 }}>{a.descripcion}<small>Responsable: {nombre(a.responsable_requerido)}</small></p></div>)
        : <p className="list-item"><span className="list-icon"><IconCheck size={18} strokeWidth={2.5} /></span>No se requieren acciones correctivas adicionales.</p>}</Panel>
    </div>

    {/* 4. Pendientes */}
    <Panel title="Datos pendientes" actions={pendientesPorPaso.length ? <span className="badge warn">{pendientesPorPaso.length} pendiente{pendientesPorPaso.length === 1 ? '' : 's'}</span> : undefined}>{pendientesPorPaso.length
      ? <>{pendientesPorPaso.map((p, i) => <div className="row" key={i}><div><strong>P{p.paso} · {etiqueta(p.campo)}</strong><small>{p.motivo}</small></div><button className="btn-sm" onClick={() => navigate('evaluacion', e.id_unidad, p.paso)}>Completar este dato</button></div>)}<div className="actions" style={{ marginTop: 12 }}><button className="primary" onClick={() => navigate('evaluacion', e.id_unidad, pendientesPorPaso[0]?.paso)}>Completar datos</button></div></>
      : <p className="muted">No hay datos pendientes.</p>}</Panel>

    {/* 5. Próximo control */}
    <Panel title="Próximo control"><div className="metrics">
      <div><span>Próximo control</span><strong>{fechaRelativa(e.fecha_proximo_control)}</strong><small>{fecha(e.fecha_proximo_control)}</small></div>
      <div><span>Vencimiento de la autorización</span><strong>{fechaRelativa(e.fecha_vencimiento_autorizacion)}</strong><small>{fecha(e.fecha_vencimiento_autorizacion)}</small></div>
    </div></Panel>

    {/* Fundamento técnico: plegado por defecto */}
    <details className="panel">
      <summary><strong>Ver fundamento técnico</strong></summary>
      <div className="stack">
        <p className="mono muted" style={{ margin: 0, fontSize: 13 }}>{e.decision_final} · decisión Mamdani</p>
        {x && <Explicado x={x} />}
        <h3>Motivos, evidencias y fuentes</h3>
        {e.motivos.map(m => <details key={m.id} className="reason"><summary><span className="badge">{m.regla}</span> {m.mensaje}</summary><p>Fundamento: {nombre(m.fundamento)}</p>{m.evidencias.map((ev, i) => <p key={i}>{etiqueta(ev.campo)}: {String(ev.valor_observado ?? 'Desconocido')} {ev.unidad} {ev.operador && `· ${ev.operador} ${ev.umbral ?? ''}`} · {fecha(ev.fecha_observacion)}</p>)}{m.fuentes.map((f, i) => <div key={i}><strong>{f.id_fuente}</strong> {f.localizador}<Source text={catalogo.data?.fuentes.find(s => s.id === f.id_fuente)?.referencia_markdown || 'Fuente disponible en la base de conocimiento'} /></div>)}</details>)}
        <p>Reglas activadas: {e.reglas_activadas.join(', ') || 'Sin activaciones: revisar los datos pendientes'}</p>
        <p>El índice expresa el nivel de intervención del modelo. La vigencia depende de las fechas de observación y de los eventos posteriores registrados.</p>
        <h3>Observaciones utilizadas</h3>
        <div className="table-scroll"><table><thead><tr><th>Campo</th><th>Valor</th><th>Estado</th><th>Procedencia</th><th>Fecha</th></tr></thead><tbody>{e.observaciones_aplicadas.map(o => <tr key={o.id}><td>{etiqueta(o.entrada.campo)}</td><td>{o.entrada.valor === null ? 'Sin dato' : String(o.entrada.valor)}</td><td>{o.estado_dato || 'No aplica'}</td><td>{o.procedencia}</td><td>{fecha(o.entrada.fecha_observacion)}</td></tr>)}</tbody></table></div>
        <p className="muted">Base {e.version_base} · Parámetros {e.version_parametros} · Motor {e.version_motor}{x ? ` · Huella ${x.hash_base.slice(0, 12)}` : ''} · {e.id}</p>
      </div>
    </details>
  </div>
}

function Explicado({ x }: { x: Explicacion }) {
  return <div className="stack"><h3>Cálculo y trazabilidad</h3><p>{x.resumen}</p>
    <p>Las reglas de la matriz se evalúan en paralelo. No hay hechos intermedios ni encadenamiento de decisiones.</p>
    <div className="table-scroll"><table><thead><tr><th>Regla</th><th>Antecedentes</th><th>Consecuente</th></tr></thead><tbody>{x.cadena.map(p => <tr key={p.orden}><td>{p.regla}</td><td>{p.porque.join('; ')}</td><td>{p.conclusion}</td></tr>)}</tbody></table></div>
  </div>
}

export function Source({ text }: { text: string }) {
  const chunks = text.split(/(\[[^\]]+\]\(https?:\/\/[^)]+\))/g)
  return <p className="source">{chunks.map((part, i) => { const m = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/); return m ? <a key={i} href={m[2]} target="_blank" rel="noreferrer">{m[1]}</a> : <span key={i}>{part.replaceAll('<br>', ' ')}</span> })}</p>
}
