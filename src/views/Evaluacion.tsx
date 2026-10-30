import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, write, revisiones, nombre, type Unidad, type EvaluacionEntrada, type Resultado, type Schema } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, PageHeader, SkeletonPage } from '../components/Shared'
import Captura, { convertir, etiqueta, validarCaptura } from '../components/Captura'
import InspeccionMatricial from '../components/InspeccionMatricial'
import EditarUnidad from '../components/EditarUnidad'
import { useAppNavigate, useId } from '../App'
import useCapturaEvaluacion from '../hooks/useCapturaEvaluacion'

const pasos = ['Lote y modalidad', 'Mediciones', 'Inspección y revisión']
const camposModelo = new Set(['humedad_grano', 'temperatura_grano', 'hr_almacen', 'estado_fisico_sanitario', 'estado_barrera', 'procedimiento_interno'])
export default function Evaluacion() {
  const id = useId(), ir = useAppNavigate()
  const q = useQuery({ queryKey: ['unidades'], queryFn: () => list<Unidad>('/unidades'), enabled: !id })
  if (id) return <Formulario key={id} id={id} />
  return <div className="stack"><PageHeader title="Evaluaciones" description="Selecciona una unidad para registrar las entradas del modelo Mamdani." /><ErrorMessage error={q.error} />{q.isLoading ? <SkeletonPage /> : q.data?.length ? <div className="unit-picker">{q.data.map(u => <article className="unit-card" key={u.id}><h3>{u.nombre_recipiente}</h3><p>{nombre(u.tipo_almacenamiento ?? '')}</p><div className="actions"><button className="primary" onClick={() => ir('evaluacion', u.id)}>Evaluar</button><button onClick={() => ir('seguimiento', u.id)}>Historial</button></div></article>)}</div> : <Empty title="No hay unidades registradas">Registra un almacén, lote y unidad desde Inicio.</Empty>}</div>
}

function Formulario({ id }: { id: string }) {
  const qc = useQueryClient(), ir = useAppNavigate()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const key = `captura:${perfil?.id}:${id}`
  const f = useCapturaEvaluacion(key, id)
  const unidad = useQuery({ queryKey: ['unidad', id], queryFn: () => request<Unidad>(`/unidades/${id}`) })
  const [busy, setBusy] = useState(false)
  const hermetico = unidad.data?.tipo_almacenamiento === 'HERMETICO'
  const datos = Object.fromEntries(Object.entries(f.form.datos).filter(([k]) => camposModelo.has(k) && (hermetico || !['estado_barrera','procedimiento_interno'].includes(k))))
  function body(): EvaluacionEntrada {
    if (!unidad.data) throw new Error('Espera a que cargue la unidad.')
    return { ...revisiones(unidad.data), fase: f.form.fase || 'INGRESO', observaciones: convertir(datos), dias_previstos_restantes: null, fecha_salida_prevista: null,
      historial: { fecha_inicio_historial: null, vida_previa_documentada: null, evidencia_vida_previa: null, intervalos_historial: [] } }
  }
  async function enviar(borrador: boolean) {
    f.setError(null); setBusy(true)
    try {
      const errores = validarCaptura(datos)
      if (Object.keys(errores).length) throw new Error(Object.entries(errores).map(([k,v]) => `${etiqueta(k)}: ${v.mensaje}`).join(' '))
      if (borrador) {
        const b = await write<Schema['Borrador']>(`/unidades/${id}/borrador`, body(), 'PUT', f.draftRevision ? { 'If-Match': `"${f.draftRevision}"` } : { 'If-None-Match': '*' })
        f.setDraftRevision(b.revision); f.setMessage('Borrador guardado. Todavía no se ha calculado una recomendación.')
      } else {
        const r = await write<Resultado>(`/unidades/${id}/evaluaciones`, body())
        sessionStorage.removeItem(key); await qc.invalidateQueries(); ir('resultado', r.evaluacion.id)
      }
    } catch (e) { f.setError(e) } finally { setBusy(false) }
  }
  if (unidad.isLoading || !f.draftLoaded) return <SkeletonPage label="Cargando captura…" />
  return <div className="stack"><PageHeader title="Evaluar unidad" eyebrow="Mamdani matricial · 320 reglas" description={unidad.data?.nombre_recipiente} back={{ label: 'Volver a evaluaciones', onClick: () => ir('evaluacion') }} actions={<button disabled={busy} onClick={() => void enviar(true)}>Guardar borrador</button>} />
    <div className="steps">{pasos.map((p,i) => <button key={p} className={f.step === i+1 ? 'active' : ''} onClick={() => f.setStep(i+1)} aria-current={f.step === i+1 ? 'step' : undefined}><span className="step-mark">{i+1}</span>{p}</button>)}</div>
    <ErrorMessage error={f.error || unidad.error} />{f.message && <p role="status" className="message">{f.message}</p>}
    <Panel title={pasos[f.step-1] ?? pasos[0]}>
      {f.step === 1 && <div className="stack"><p>{hermetico ? 'Matriz hermética: 64 reglas; la HR ambiental no participa.' : 'Matriz no hermética: 256 reglas y cuatro entradas.'}</p><Field label="Fase del registro"><select value={f.form.fase || 'INGRESO'} onChange={e => f.setForm(v => ({ ...v, fase: e.target.value as 'INGRESO' | 'SEGUIMIENTO' }))}><option value="INGRESO">Ingreso</option><option value="SEGUIMIENTO">Seguimiento</option></select></Field>{unidad.data && <EditarUnidad unidad={unidad.data} />}<p className="muted">La fase identifica el registro. La recomendación se obtiene únicamente de las entradas de la matriz seleccionada.</p></div>}
      {f.step === 2 && <><p>Registra mediciones representativas con fecha y método. Para humedad utiliza INSTRUMENTAL o LABORATORIO como método. La ventana de siete días es una política del prototipo.</p><Captura datos={f.form.datos} historicos={f.historicos} filtro={['humedad_grano','temperatura_grano', ...(!hermetico ? ['hr_almacen'] : [])]} onChange={datos => f.setForm(v => ({ ...v, datos }))} /></>}
      {f.step === 3 && <><InspeccionMatricial datos={f.form.datos} historicos={f.historicos} hermetico={hermetico} onChange={datos => f.setForm(v => ({ ...v, datos }))} /><h3>Revisión antes del cálculo</h3><p>Se conservarán observaciones, procedencia, pertenencias, reglas activadas y centroide. Un dato pendiente no se sustituye por cero.</p><div className="review-list">{Object.entries(datos).map(([k,v]) => <p key={k}><strong>{etiqueta(k)}:</strong> {v.valor || 'Sin dato'} · {v.fecha.replace('T',' ')}</p>)}</div></>}
    </Panel><div className="actions sticky-actions"><button disabled={f.step === 1} onClick={() => f.setStep(v => v-1)}>Anterior</button>{f.step < 3 ? <button className="primary" onClick={() => f.setStep(v => v+1)}>Siguiente</button> : <button className="primary" disabled={busy || !unidad.data} onClick={() => void enviar(false)}>{busy ? 'Calculando…' : 'Calcular y registrar evaluación'}</button>}</div>
  </div>
}
