import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, list, nombre, request, write, revisiones, type Unidad, type EvaluacionEntrada, type Resultado, type Schema } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, PageHeader, Skeleton, SkeletonPage } from '../components/Shared'
import { useToast } from '../components/Toast'
import { IconAlert, IconCheck, IconClipboard, IconLoader } from '../components/Icons'
import { convertir, etiqueta, ErroresCaptura, validarCaptura, type CapturaDatos, type ErrorCampo } from '../components/Captura'
import campos from '../campos.json'
import { useAppNavigate, useId, usePaso } from '../App'
import EditarUnidad from '../components/EditarUnidad'
import Verificaciones from '../components/Verificaciones'
import MedicionesAlmacenamiento, { entradasAlmacenamiento } from '../components/MedicionesAlmacenamiento'
import useCapturaEvaluacion, { pasosEvaluacion as steps, pasoCompacto } from '../hooks/useCapturaEvaluacion'

const textoCaptura = { APORTADO: 'Aportado', DESCONOCIDO: 'No se sabe', NO_APLICA: 'No aplica' } as const
const etiquetasIntervalo: Record<string, string> = { inicio: 'Inicio', fin: 'Fin', humedad: 'Humedad del grano (% b.h.)', temperatura: 'Temperatura del grano (°C)', metodo: 'Método', evidencia: 'Evidencia' }
const etiquetasExtra: Record<string, string> = { vida: 'Vida previa documentada', dias: 'Días previstos restantes', inicio: 'Inicio del historial', salida: 'Salida prevista' }
/** Paso del asistente en el que se captura un campo (el mismo criterio que la revisión final). */
const pasoDe = (campo: string) => entradasAlmacenamiento.includes(campo) ? 2 : pasoCompacto(campos[campo as keyof typeof campos]?.paso ?? 1)
const esNumero = (v: string) => !v.trim() || Number.isFinite(Number(v.replace(',', '.')))

function mostrar(campo: string, v: CapturaDatos[string]) {
  if (v.captura !== 'APORTADO') return v.captura === 'NO_APLICA' && v.causa ? `No aplica (${v.causa})` : textoCaptura[v.captura]
  const def = campos[campo as keyof typeof campos]
  if (def?.tipo === 'B') return v.valor === 'true' ? 'Sí' : 'No'
  if (def?.tipo === 'F') return new Date(v.valor).toLocaleString('es-PE', { timeZone: 'America/Lima', dateStyle: 'medium', timeStyle: 'short' })
  return `${v.valor}${def?.tipo === 'N' && def.unidad ? ' ' + ({ PCT_BH: '% b.h.', PCT_HR: '% HR', PCT_MASA: '% masa', CELSIUS: '°C', METROS: 'm', DIAS: 'días', FRACCION: '' } as Record<string, string>)[def.unidad] : ''}`
}

/** Abre los grupos plegados que contienen el campo, lo centra y le pasa el foco. */
function enfocarCampo(id: string) {
  window.setTimeout(() => {
    const el = document.getElementById(id)
    if (!el) return
    for (let d = el.closest('details'); d; d = d.parentElement?.closest('details') ?? null) d.open = true
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    el.querySelector<HTMLElement>('[aria-invalid="true"], input, select, textarea')?.focus({ preventScroll: true })
  }, 80)
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
  const [erroresCampo, setErroresCampo] = useState<Record<string, ErrorCampo>>({})
  const [erroresExtra, setErroresExtra] = useState<Record<string, string>>({})
  const unidad = useQuery({ queryKey: ['unidad', id], queryFn: () => request<Unidad>(`/unidades/${id}`) })
  const limpiarCampo = (campo: string) => setErroresCampo(e => { const { [campo]: _, ...resto } = e; return resto })
  const limpiarExtra = (k: string) => setErroresExtra(e => { const { [k]: _, ...resto } = e; return resto })

  /** Todos los problemas de la captura a la vez, con el paso al que pertenece cada uno. */
  function validar() {
    const porCampo = validarCaptura(form.datos)
    const extra: Record<string, string> = {}
    if (!esNumero(form.vida)) extra.vida = 'Escribe una fracción entre 0 y 1.'
    if (!esNumero(form.dias)) extra.dias = 'Escribe un número de días.'
    form.intervalos.forEach((it, i) => {
      if (!it.inicio || !it.fin) extra[`intervalo-${i}`] = 'Indica el inicio y el fin del intervalo.'
      else if (!esNumero(it.humedad) || !esNumero(it.temperatura)) extra[`intervalo-${i}`] = 'Revisa la humedad y la temperatura: deben ser números.'
    })
    return { porCampo, extra }
  }
  const pendientes = [
    ...Object.entries(erroresCampo).map(([campo, e]) => ({ id: `campo-${campo}`, paso: pasoDe(campo), etiqueta: etiqueta(campo), mensaje: e.mensaje })),
    ...Object.entries(erroresExtra).map(([k, mensaje]) => ({ id: `campo-${k}`, paso: 2, etiqueta: k.startsWith('intervalo-') ? `Intervalo ${Number(k.split('-')[1]) + 1} del historial` : etiquetasExtra[k] ?? k, mensaje })),
  ].sort((a, b) => a.paso - b.paso)
  const porPaso = (n: number) => pendientes.filter(p => p.paso === n).length
  function irA(p: { id: string; paso: number }) { setStep(p.paso); enfocarCampo(p.id) }

  function body(): EvaluacionEntrada {
    if (!unidad.data) throw new Error('Espera a que cargue la unidad')
    const numero = (v: string) => { if (!v) return null; const n = Number(v.replace(',', '.')); if (!Number.isFinite(n)) throw new Error('Revisa los valores numéricos'); return n }
    return { ...revisiones(unidad.data), fase: form.fase || null, observaciones: convertir(form.datos), dias_previstos_restantes: numero(form.dias), fecha_salida_prevista: form.salida ? new Date(form.salida).toISOString() : null,
      historial: { fecha_inicio_historial: form.inicio ? new Date(form.inicio).toISOString() : null, vida_previa_documentada: numero(form.vida), evidencia_vida_previa: form.evidencia || null, intervalos_historial: form.intervalos.map(i => ({ inicio: new Date(i.inicio).toISOString(), fin: new Date(i.fin).toISOString(), humedad_grano: numero(i.humedad), temperatura_grano: numero(i.temperatura), metodo: i.metodo || null, evidencia: i.evidencia || null })) } }
  }
  async function submit(draft: boolean) {
    setError(null); setMessage('')
    const { porCampo, extra } = validar()
    setErroresCampo(porCampo); setErroresExtra(extra)
    const primero = Object.keys(porCampo).map(c => ({ id: `campo-${c}`, paso: pasoDe(c) })).concat(Object.keys(extra).map(k => ({ id: `campo-${k}`, paso: 2 }))).sort((a, b) => a.paso - b.paso)[0]
    if (primero) { irA(primero); return }
    setBusy(true)
    try {
      if (draft) {
        const b = await write<Schema['Borrador']>(`/unidades/${id}/borrador`, body(), 'PUT', draftRevision ? { 'If-Match': `"${draftRevision}"` } : { 'If-None-Match': '*' })
        setDraftRevision(b.revision); setMessage('Borrador guardado en el servidor. No constituye una evaluación.')
      } else {
        const result = await write<Resultado>(`/unidades/${id}/evaluaciones`, body())
        sessionStorage.removeItem(key); await qc.invalidateQueries(); avisar('Evaluación emitida', 'Revisa la decisión y su explicación.'); navigate('resultado', result.evaluacion.id)
      }
    } catch (err) {
      // 422 del servidor: "observaciones.N…" se traduce al campo N de la captura.
      const claves = Object.keys(form.datos)
      const delServidor = err instanceof ApiError ? Object.fromEntries(err.campos.flatMap(c => {
        const n = /observaciones\.(\d+)/.exec(c.ruta)?.[1]
        return n !== undefined && claves[Number(n)] ? [[claves[Number(n)], { tipo: 'valor' as const, mensaje: c.mensaje }]] : []
      })) : {}
      if (Object.keys(delServidor).length) { setErroresCampo(delServidor); const c = Object.keys(delServidor)[0]; irA({ id: `campo-${c}`, paso: pasoDe(c) }) }
      else setError(err)
    } finally { setBusy(false) }
  }
  const set = (k: keyof typeof form, v: string) => { if (erroresExtra[k]) limpiarExtra(k); setForm(f => ({ ...f, [k]: v })) }
  if (unidad.isLoading || !draftLoaded) return <SkeletonPage label="Cargando la captura…" />
  const aportadas = Object.values(form.datos).filter(d => d.captura === 'APORTADO').length
  return <div className="stack">
    <PageHeader back={{ label: 'Volver al inicio', onClick: () => navigate('dashboard') }} eyebrow={`Captura guiada · Paso ${step} de 4`} title="Evaluar unidad"
      description={<>{unidad.data?.nombre_recipiente}{unidad.data?.tipo_almacenamiento && ` · ${nombre(unidad.data.tipo_almacenamiento)}`}</>}
      actions={<button disabled={busy} onClick={() => void submit(true)}>Guardar borrador</button>} />
    <div className="stack compact" style={{ marginTop: 0 }}>
      <div className="progress" role="progressbar" aria-label="Progreso de la captura" aria-valuemin={1} aria-valuemax={4} aria-valuenow={step}><div style={{ width: `${((step - 0.5) / 4) * 100}%` }} /></div>
      <div className="steps">{steps.map((s, i) => {
        const n = i + 1, actual = step === n, hecho = step > n, faltan = porPaso(n)
        return <button key={s} className={[actual ? 'active' : hecho && !faltan ? 'done' : '', faltan ? 'has-error' : ''].join(' ').trim()} aria-current={actual ? 'step' : undefined} onClick={() => setStep(n)}>
          <span className="step-mark" aria-hidden="true">{faltan ? '!' : hecho ? <IconCheck size={13} strokeWidth={3} /> : n}</span>
          <span className="step-label"><b>P{n}</b><span>{s}</span>{faltan > 0 && <span className="step-error">{faltan} por completar</span>}</span>
        </button>
      })}<button disabled><span className="step-mark" aria-hidden="true">4</span><span className="step-label"><b>P4</b><span>Resultado</span></span></button></div>
    </div>
    {pendientes.length > 0 && <div role="alert" className="message error resumen-errores"><IconAlert size={20} />
      <div><strong>Faltan {pendientes.length} {pendientes.length === 1 ? 'dato' : 'datos'} antes de guardar o enviar</strong>
        <span>Corrige los campos marcados en rojo; el resto de tu captura se conserva.</span>
        <ul>{pendientes.map(p => <li key={p.id}><span className="paso-tag">P{p.paso} · {steps[p.paso - 1]}</span><span><strong>{p.etiqueta}:</strong> {p.mensaje}</span><button className="btn-sm" onClick={() => irA(p)}>Ir al campo</button></li>)}</ul>
      </div>
    </div>}
    <ErrorMessage error={error || unidad.error} />{message && <p role="status" className="message ok">{message}</p>}
    <div className="actions"><button className="btn-sm" onClick={() => { void unidad.refetch(); setMessage('Revisiones actualizadas; comprueba los datos antes de reenviar.') }}>Actualizar revisiones</button>{draftRevision && <button className="btn-sm" onClick={() => void request<Schema['Borrador']>(`/unidades/${id}/borrador`).then(b => { setDraftRevision(b.revision); restore(b.contenido) }).catch(setError)}>Reemplazar captura por borrador del servidor</button>}</div>
    <ErroresCaptura.Provider value={{ errores: erroresCampo, limpiar: limpiarCampo }}>
    <Panel title={steps[step - 1]}><p className="muted">No se sabe es diferente de No. Puedes enviar información parcial: un hallazgo de moho no necesita esperar las otras mediciones.</p>
      {step === 1 && <div className="form-grid"><Field label="Fase"><select value={form.fase} onChange={e => set('fase', e.target.value)}><option value="">Sin definir</option><option value="INGRESO">Ingreso</option><option value="SEGUIMIENTO">Seguimiento</option></select></Field>
        <dl className="stack compact" style={{ margin: 0 }}><div><dt className="muted" style={{ fontSize: 12 }}>Modalidad</dt><dd style={{ margin: 0 }}>{unidad.data?.tipo_almacenamiento ? nombre(unidad.data.tipo_almacenamiento) : 'Sin definir'}</dd></div><div><dt className="muted" style={{ fontSize: 12 }}>Producto</dt><dd style={{ margin: 0 }}>Maíz chulpi · Alimentación</dd></div><div><dt className="muted" style={{ fontSize: 12 }}>Responsable</dt><dd style={{ margin: 0 }}>{perfil?.nombre}</dd></div></dl></div>}
      {step === 1 && unidad.data && <EditarUnidad unidad={unidad.data} />}
      {step === 2 && <MedicionesAlmacenamiento historicos={historicos} datos={form.datos} onChange={datos => setForm(f => ({ ...f, datos }))} hermetico={unidad.data?.tipo_almacenamiento === 'HERMETICO'}/>}
      {step === 3 && <Verificaciones datos={form.datos} historicos={historicos} onChange={datos => setForm(f => ({ ...f, datos }))} idAlmacen={unidad.data?.id_almacen} />}

      {step === 2 && <details className="capture-group" open style={{ marginTop: 16 }}><summary>Plazo e historial documentado</summary><div className="stack"><h3>Tiempo documentado</h3><p className="muted" style={{ margin: 0 }}>La vida previa es una fracción del tiempo de referencia, nunca un porcentaje de seguridad. El cero requiere constancia de origen.</p><div className="form-grid" style={{ marginTop: 0 }}>
        <Field label="Inicio del historial"><input type="datetime-local" value={form.inicio.slice(0,16)} onChange={e => set('inicio', e.target.value)} /></Field>
        <div id="campo-vida"><Field label="Vida previa documentada (fracción)" hint="Entre 0 y 1." error={erroresExtra.vida}><input inputMode="decimal" value={form.vida} onChange={e => set('vida', e.target.value)} /></Field></div>
        <Field label="Evidencia de la vida previa"><input value={form.evidencia} onChange={e => set('evidencia', e.target.value)} /></Field>
        <div id="campo-dias"><Field label="Días previstos restantes" error={erroresExtra.dias}><input inputMode="numeric" value={form.dias} onChange={e => set('dias', e.target.value)} /></Field></div>
        <Field label="Salida prevista"><input type="datetime-local" value={form.salida.slice(0,16)} onChange={e => set('salida', e.target.value)} /></Field></div>
        <h3>Intervalos del historial</h3>{form.intervalos.map((item, i) => { const err = erroresExtra[`intervalo-${i}`]
          return <div className={`panel form-grid${err ? ' invalid' : ''}`} id={`campo-intervalo-${i}`} key={i} style={{ marginTop: 0 }}>
            {err && <p className="field-error" style={{ gridColumn: '1 / -1', margin: 0 }}><IconAlert size={14} />{err}</p>}
            {Object.entries(item).map(([k, v]) => <Field key={k} label={`${etiquetasIntervalo[k] ?? k} · intervalo ${i + 1}`}><input type={k === 'inicio' || k === 'fin' ? 'datetime-local' : 'text'} inputMode={k === 'humedad' || k === 'temperatura' ? 'decimal' : undefined} aria-invalid={err && ((k === 'inicio' && !item.inicio) || (k === 'fin' && !item.fin) || ((k === 'humedad' || k === 'temperatura') && !esNumero(v))) ? true : undefined} value={v} onChange={e => { if (err) limpiarExtra(`intervalo-${i}`); setForm(f => ({ ...f, intervalos: f.intervalos.map((it, n) => n === i ? { ...it, [k]: e.target.value } : it) })) }} /></Field>)}
            <button className="btn-danger btn-sm" onClick={() => { limpiarExtra(`intervalo-${i}`); setForm(f => ({ ...f, intervalos: f.intervalos.filter((_, n) => n !== i) })) }}>Quitar intervalo</button></div> })}
        <div className="actions"><button className="btn-sm" onClick={() => setForm(f => ({ ...f, intervalos: [...f.intervalos, { inicio: '', fin: '', humedad: '', temperatura: '', metodo: '', evidencia: '' }] }))}>Añadir intervalo</button></div><p className="muted" style={{ margin: 0 }}>Los planes de monitoreo y dictámenes se registran desde Seguimiento.</p></div></details>}
      {step === steps.length && <><p>{aportadas} observaciones aportadas. Los campos omitidos permanecen desconocidos o conservan su dato histórico identificado por el servidor.</p><div className="review-list">{Object.entries(form.datos).map(([k,v]) => <p key={k} style={erroresCampo[k] ? { color: 'var(--color-crit-ink)' } : undefined}><strong>{etiqueta(k)}:</strong> {mostrar(k, v)}{erroresCampo[k] && ' · incompleto'} <button className="btn-ghost btn-sm" onClick={() => { setStep(pasoDe(k)); if (erroresCampo[k]) enfocarCampo(`campo-${k}`) }}>Editar</button></p>)}</div><p className="muted">La decisión y su vigencia se calcularán en el servidor.</p></>}
    </Panel>
    </ErroresCaptura.Provider>
    <div className="actions sticky-actions"><span className="muted desktop-only" style={{ fontSize: 13 }}>{pendientes.length ? <span style={{ color: 'var(--color-crit-ink)', fontWeight: 600 }}>{pendientes.length} por completar</span> : `${aportadas} observaciones aportadas`}</span><div className="actions"><button disabled={step === 1} onClick={() => setStep(s => s - 1)}>Anterior</button>{step < steps.length && <button onClick={() => setStep(s => s + 1)}>Siguiente</button>}<button className="primary" disabled={busy || !unidad.data} onClick={() => void submit(false)}>{busy ? <><IconLoader size={16} className="spin" />Guardando…</> : 'Enviar y evaluar'}</button></div></div>
  </div>
}
