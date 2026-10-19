import { useEffect, useState } from 'react'
import { ApiError, request, type EvaluacionEntrada, type Schema } from '../api/client'
import { desdeObservaciones, fechaLocal, type CapturaDatos } from '../components/Captura'

export const pasosEvaluacion = ['Lote y modalidad', 'Mediciones y plazo', 'Verificaciones']
export const pasoCompacto = (paso: number) => paso === 1 ? 1 : paso === 2 || paso === 5 ? 2 : 3
export const formularioVacio = () => ({ datos: {} as CapturaDatos, fase: '' as '' | 'INGRESO' | 'SEGUIMIENTO', dias: '', salida: '', inicio: '', vida: '', evidencia: '', intervalos: [] as { inicio: string; fin: string; humedad: string; temperatura: string; metodo: string; evidencia: string }[] })
type Formulario = ReturnType<typeof formularioVacio>

function leer(key: string): { form: Formulario; step: number; local: boolean } {
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || 'null')
    const form = saved?.form ?? saved
    if (form && typeof form === 'object' && form.datos && Array.isArray(form.intervalos)) {
      return { form: { ...formularioVacio(), ...form }, step: Math.max(1,Math.min(pasosEvaluacion.length,(saved.versionFlujo === 2 ? Number(saved.step) : pasoCompacto(Number(saved.step) || 1))||1)), local: true }
    }
  } catch { /* Un borrador corrupto no debe bloquear el acceso al historial. */ }
  return { form: formularioVacio(), step: 1, local: false }
}

export function formularioDesde(b: EvaluacionEntrada): Formulario {
  return { datos: desdeObservaciones(b.observaciones), fase: b.fase || '', dias: b.dias_previstos_restantes?.toString() ?? '', salida: b.fecha_salida_prevista ? fechaLocal(b.fecha_salida_prevista) : '', inicio: b.historial.fecha_inicio_historial ? fechaLocal(b.historial.fecha_inicio_historial) : '', vida: b.historial.vida_previa_documentada?.toString() ?? '', evidencia: b.historial.evidencia_vida_previa || '', intervalos: b.historial.intervalos_historial.map(i => ({ inicio: fechaLocal(i.inicio), fin: fechaLocal(i.fin), humedad: i.humedad_grano?.toString() ?? '', temperatura: i.temperatura_grano?.toString() ?? '', metodo: i.metodo || '', evidencia: i.evidencia || '' })) }
}

export default function useCapturaEvaluacion(key: string, id: string, pasoSolicitado?: number) {
  const [inicial] = useState(() => leer(key))
  const [form, setForm] = useState(inicial.form), [step, setStep] = useState(pasoSolicitado ?? inicial.step)
  const [historicos, setHistoricos] = useState<CapturaDatos>({})
  const [draftRevision, setDraftRevision] = useState<number | null>(null)
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [error, setError] = useState<unknown>(null), [message, setMessage] = useState('')
  useEffect(() => { if (draftLoaded) sessionStorage.setItem(key, JSON.stringify({ versionFlujo: 2, form, step })) }, [key, form, step, draftLoaded])
  useEffect(() => {
    let activo = true
    void Promise.all([
      request<Schema['Borrador']>(`/unidades/${id}/borrador`).catch(e => { if (e instanceof ApiError && e.status === 404) return null; throw e }),
      request<Schema['CapturaAnterior']>(`/unidades/${id}/captura-anterior`).catch(e => { if (e instanceof ApiError && e.status === 404) return null; throw e }),
    ]).then(([borrador, anterior]) => {
      if (!activo) return
      if (anterior) setHistoricos(desdeObservaciones(anterior.contenido.observaciones))
      if (borrador) {
        setDraftRevision(borrador.revision)
        if (inicial.local) setMessage('Tu captura local está recuperada. También hay un borrador del servidor: puedes elegir recuperarlo.')
        else { setForm(formularioDesde(borrador.contenido)); setMessage('Borrador recuperado.') }
      } else if (!inicial.local && anterior) {
        setForm({ ...formularioDesde(anterior.contenido), datos: {} })
        setMessage('Se muestran los datos anteriores con su fecha. Solo los campos que modifiques se registrarán como nuevas observaciones; revisa la fase y los plazos.')
      }
    }).catch(e => { if (activo) setError(e) }).finally(() => { if (activo) setDraftLoaded(true) })
    return () => { activo = false }
  }, [id, inicial.local])
  function restore(b: EvaluacionEntrada) { setForm(formularioDesde(b)); setMessage('Borrador recuperado. Se reemplazó la captura local.') }
  return { form, setForm, step, setStep, historicos, draftRevision, setDraftRevision, draftLoaded, error, setError, message, setMessage, restore }
}
