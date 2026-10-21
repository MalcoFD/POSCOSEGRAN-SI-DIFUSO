import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, nombre, request, write, revisiones, type Unidad, type EvaluacionEntrada, type Resultado, type Schema } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, PageHeader, Skeleton, SkeletonPage } from '../components/Shared'
import { useToast } from '../components/Toast'
import { IconCheck, IconClipboard, IconLoader } from '../components/Icons'
import { convertir, etiqueta, type CapturaDatos } from '../components/Captura'
import campos from '../campos.json'
import { useAppNavigate, useId, usePaso } from '../App'
import EditarUnidad from '../components/EditarUnidad'
import Verificaciones from '../components/Verificaciones'
import MedicionesAlmacenamiento, { entradasAlmacenamiento } from '../components/MedicionesAlmacenamiento'
import useCapturaEvaluacion, { pasosEvaluacion as steps, pasoCompacto } from '../hooks/useCapturaEvaluacion'

const textoCaptura = { APORTADO: 'Aportado', DESCONOCIDO: 'No se sabe', NO_APLICA: 'No aplica' } as const
const etiquetasIntervalo: Record<string, string> = { inicio: 'Inicio', fin: 'Fin', humedad: 'Humedad del grano (% b.h.)', temperatura: 'Temperatura del grano (°C)', metodo: 'Método', evidencia: 'Evidencia' }
function mostrar(campo: string, v: CapturaDatos[string]) {
  if (v.captura !== 'APORTADO') return v.captura === 'NO_APLICA' && v.causa ? `No aplica (${v.causa})` : textoCaptura[v.captura]
  const def = campos[campo as keyof typeof campos]
  if (def?.tipo === 'B') return v.valor === 'true' ? 'Sí' : 'No'
  if (def?.tipo === 'F') return new Date(v.valor).toLocaleString('es-PE', { timeZone: 'America/Lima', dateStyle: 'medium', timeStyle: 'short' })
  return `${v.valor}${def?.tipo === 'N' && def.unidad ? ' ' + ({ PCT_BH: '% b.h.', PCT_HR: '% HR', PCT_MASA: '% masa', CELSIUS: '°C', METROS: 'm', DIAS: 'días', FRACCION: '' } as Record<string, string>)[def.unidad] : ''}`
}

export default function Evaluacion() {
  const id = useId(), navigate = useAppNavigate()
  const unidades = useQuery({ queryKey: ['unidades'], queryFn: () => list<Unidad>('/unidades'), enabled: !id })
  if (!id) return <div className="stack">
    <PageHeader eyebrow="Captura guiada" title="Evaluaciones" description="Elige la unidad que quieres evaluar." />
    <ErrorMessage error={unidades.error} onRetry={() => void unidades.refetch()} />
    {unidades.isLoading ? <div className="unit-picker" aria-busy="true">{[0, 1, 2].map(i => <div className="unit-card" key={i} aria-hidden="true"><Skeleton className="sk-line" width="60%" height={14} /><Skeleton className="sk-line" width="40%" /><Skeleton className="sk-btn" width={90} height={36} /></div>)}<span className="sr-only">Cargando unidades…</span></div>
      : unidades.data?.length ? <div className="unit-picker">{unidades.data.map(u => <article className="unit-card" key={u.id}>
        <header><div><strong>{u.nombre_recipiente}</strong><small>{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Modalidad sin definir'}</small></div></header>
        <div className="actions"><button className="primary btn-sm" onClick={() => navigate('evaluacion', u.id)}>Evaluar</button><button className="btn-sm" onClick={() => navigate('seguimiento', u.id)}>Seguimiento</button></div>
      </article>)}</div>
      : <Empty title="No hay unidades para evaluar" icon={<IconClipboard size={26} />} action={<button className="primary" onClick={() => navigate('dashboard')}>Ir a Inicio</button>}>Registra una unidad desde Inicio para comenzar la captura.</Empty>}
  </div>
  return <Formulario key={id} id={id} />
}

function Formulario({ id }: { id: string }) {
  const navigate = useAppNavigate(), qc = useQueryClient(), avisar = useToast()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const pasoSolicitado = usePaso()
  const key = `captura:${perfil?.id}:${id}`
  const { form, setForm, step, setStep, historicos, draftRevision, setDraftRevision, draftLoaded, error, setError, message, setMessage, restore } = useCapturaEvaluacion(key, id, pasoSolicitado ? pasoCompacto(pasoSolicitado) : undefined)
  const [busy, setBusy] = useState(false)
  const unidad = useQuery({ queryKey: ['unidad', id], queryFn: () => request<Unidad>(`/unidades/${id}`) })
  function body(): EvaluacionEntrada {
    if (!unidad.data) throw new Error('Espera a que cargue la unidad')
    const numero = (v: string) => { if (!v) return null; const n = Number(v.replace(',', '.')); if (!Number.isFinite(n)) throw new Error('Revisa los valores numéricos'); return n }
    return { ...revisiones(unidad.data), fase: form.fase || null, observaciones: convertir(form.datos), dias_previstos_restantes: numero(form.dias), fecha_salida_prevista: form.salida ? new Date(form.salida).toISOString() : null,
      historial: { fecha_inicio_historial: form.inicio ? new Date(form.inicio).toISOString() : null, vida_previa_documentada: numero(form.vida), evidencia_vida_previa: form.evidencia || null, intervalos_historial: form.intervalos.map(i => ({ inicio: new Date(i.inicio).toISOString(), fin: new Date(i.fin).toISOString(), humedad_grano: numero(i.humedad), temperatura_grano: numero(i.temperatura), metodo: i.metodo || null, evidencia: i.evidencia || null })) } }
  }
  async function submit(draft: boolean) {
    setBusy(true); setError(null); setMessage('')
    try {
      if (draft) {
        const b = await write<Schema['Borrador']>(`/unidades/${id}/borrador`, body(), 'PUT', draftRevision ? { 'If-Match': `"${draftRevision}"` } : { 'If-None-Match': '*' })
        setDraftRevision(b.revision); setMessage('Borrador guardado en el servidor. No constituye una evaluación.')
      } else {
        const result = await write<Resultado>(`/unidades/${id}/evaluaciones`, body())
        sessionStorage.removeItem(key); await qc.invalidateQueries(); avisar('Evaluación emitida', 'Revisa la decisión y su explicación.'); navigate('resultado', result.evaluacion.id)
      }
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  if (unidad.isLoading || !draftLoaded) return <SkeletonPage label="Cargando la captura…" />
  const aportadas = Object.values(form.datos).filter(d => d.captura === 'APORTADO').length
  return <div className="stack">
    <PageHeader back={{ label: 'Volver al inicio', onClick: () => navigate('dashboard') }} eyebrow={`Captura guiada · Paso ${step} de 4`} title="Evaluar unidad"
      description={<>{unidad.data?.nombre_recipiente}{unidad.data?.tipo_almacenamiento && ` · ${nombre(unidad.data.tipo_almacenamiento)}`}</>}
      actions={<button disabled={busy} onClick={() => void submit(true)}>Guardar borrador</button>} />
    <div className="stack compact" style={{ marginTop: 0 }}>
      <div className="progress" role="progressbar" aria-label="Progreso de la captura" aria-valuemin={1} aria-valuemax={4} aria-valuenow={step}><div style={{ width: `${((step - 0.5) / 4) * 100}%` }} /></div>
      <div className="steps">{steps.map((s, i) => {
        const n = i + 1, actual = step === n, hecho = step > n
        return <button key={s} className={actual ? 'active' : hecho ? 'done' : ''} aria-current={actual ? 'step' : undefined} onClick={() => setStep(n)}>
          <span className="step-mark" aria-hidden="true">{hecho ? <IconCheck size={13} strokeWidth={3} /> : n}</span><span><b>P{n}</b><span>{s}</span></span>
        </button>
      })}<button disabled><span className="step-mark" aria-hidden="true">4</span><span><b>P4</b><span>Resultado</span></span></button></div>
    </div>
    <ErrorMessage error={error || unidad.error} />{message && <p role="status" className="message ok">{message}</p>}
    <div className="actions"><button className="btn-sm" onClick={() => { void unidad.refetch(); setMessage('Revisiones actualizadas; comprueba los datos antes de reenviar.') }}>Actualizar revisiones</button>{draftRevision && <button className="btn-sm" onClick={() => void request<Schema['Borrador']>(`/unidades/${id}/borrador`).then(b => { setDraftRevision(b.revision); restore(b.contenido) }).catch(setError)}>Reemplazar captura por borrador del servidor</button>}</div>
    <Panel title={steps[step - 1]}><p className="muted">No se sabe es diferente de No. Puedes enviar información parcial: un hallazgo de moho no necesita esperar las otras mediciones.</p>
      {step === 1 && <div className="form-grid"><Field label="Fase"><select value={form.fase} onChange={e => set('fase', e.target.value)}><option value="">Sin definir</option><option value="INGRESO">Ingreso</option><option value="SEGUIMIENTO">Seguimiento</option></select></Field>
        <dl className="stack compact" style={{ margin: 0 }}><div><dt className="muted" style={{ fontSize: 12 }}>Modalidad</dt><dd style={{ margin: 0 }}>{unidad.data?.tipo_almacenamiento ? nombre(unidad.data.tipo_almacenamiento) : 'Sin definir'}</dd></div><div><dt className="muted" style={{ fontSize: 12 }}>Producto</dt><dd style={{ margin: 0 }}>Maíz chulpi · Alimentación</dd></div><div><dt className="muted" style={{ fontSize: 12 }}>Responsable</dt><dd style={{ margin: 0 }}>{perfil?.nombre}</dd></div></dl></div>}
      {step === 1 && unidad.data && <EditarUnidad unidad={unidad.data} />}
      {step === 2 && <MedicionesAlmacenamiento historicos={historicos} datos={form.datos} onChange={datos => setForm(f => ({ ...f, datos }))} hermetico={unidad.data?.tipo_almacenamiento === 'HERMETICO'}/>}
      {step === 3 && <Verificaciones datos={form.datos} historicos={historicos} onChange={datos => setForm(f => ({ ...f, datos }))} idAlmacen={unidad.data?.id_almacen} />}

      {step === 2 && <details className="capture-group" open style={{ marginTop: 16 }}><summary>Plazo e historial documentado</summary><div className="stack"><h3>Tiempo documentado</h3><p className="muted" style={{ margin: 0 }}>La vida previa es una fracción del tiempo de referencia, nunca un porcentaje de seguridad. El cero requiere constancia de origen.</p><div className="form-grid" style={{ marginTop: 0 }}>
        <Field label="Inicio del historial"><input type="datetime-local" value={form.inicio.slice(0,16)} onChange={e => set('inicio', e.target.value)} /></Field><Field label="Vida previa documentada (fracción)" hint="Entre 0 y 1."><input inputMode="decimal" value={form.vida} onChange={e => set('vida', e.target.value)} /></Field><Field label="Evidencia de la vida previa"><input value={form.evidencia} onChange={e => set('evidencia', e.target.value)} /></Field><Field label="Días previstos restantes"><input inputMode="numeric" value={form.dias} onChange={e => set('dias', e.target.value)} /></Field><Field label="Salida prevista"><input type="datetime-local" value={form.salida.slice(0,16)} onChange={e => set('salida', e.target.value)} /></Field></div>
        <h3>Intervalos del historial</h3>{form.intervalos.map((item, i) => <div className="panel form-grid" key={i} style={{ marginTop: 0 }}>{Object.entries(item).map(([k, v]) => <Field key={k} label={`${etiquetasIntervalo[k] ?? k} · intervalo ${i + 1}`}><input type={k === 'inicio' || k === 'fin' ? 'datetime-local' : 'text'} inputMode={k === 'humedad' || k === 'temperatura' ? 'decimal' : undefined} value={v} onChange={e => setForm(f => ({ ...f, intervalos: f.intervalos.map((it, n) => n === i ? { ...it, [k]: e.target.value } : it) }))} /></Field>)}<button className="btn-danger btn-sm" onClick={() => setForm(f => ({ ...f, intervalos: f.intervalos.filter((_, n) => n !== i) }))}>Quitar intervalo</button></div>)}
        <div className="actions"><button className="btn-sm" onClick={() => setForm(f => ({ ...f, intervalos: [...f.intervalos, { inicio: '', fin: '', humedad: '', temperatura: '', metodo: '', evidencia: '' }] }))}>Añadir intervalo</button></div><p className="muted" style={{ margin: 0 }}>Los planes de monitoreo y dictámenes se registran desde Seguimiento.</p></div></details>}
      {step === steps.length && <><p>{aportadas} observaciones aportadas. Los campos omitidos permanecen desconocidos o conservan su dato histórico identificado por el servidor.</p><div className="review-list">{Object.entries(form.datos).map(([k,v]) => <p key={k}><strong>{etiqueta(k)}:</strong> {mostrar(k, v)} <button className="btn-ghost btn-sm" onClick={() => setStep(entradasAlmacenamiento.includes(k) ? 2 : pasoCompacto(campos[k as keyof typeof campos]?.paso ?? 1))}>Editar</button></p>)}</div><p className="muted">La decisión y su vigencia se calcularán en el servidor.</p></>}
    </Panel>
    <div className="actions sticky-actions"><span className="muted desktop-only" style={{ fontSize: 13 }}>{aportadas} observaciones aportadas</span><div className="actions"><button disabled={step === 1} onClick={() => setStep(s => s - 1)}>Anterior</button>{step < steps.length && <button onClick={() => setStep(s => s + 1)}>Siguiente</button>}<button className="primary" disabled={busy || !unidad.data} onClick={() => void submit(false)}>{busy ? <><IconLoader size={16} className="spin" />Guardando…</> : 'Enviar y evaluar'}</button></div></div>
  </div>
}
