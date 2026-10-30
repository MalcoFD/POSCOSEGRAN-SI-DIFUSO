import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, request, write, fecha, type Schema } from '../api/client'
import campos from '../alcance-inspeccion.json'
import Captura, { convertir, desdeObservaciones, fechaLocal, type CapturaDatos } from './Captura'
import { ErrorMessage, Field } from './Shared'

export default function InspeccionAlmacen({id,revision}: {id:string;revision:number}) {
  const qc=useQueryClient()
  const [datos,setDatos]=useState<CapturaDatos>({}),[editar,setEditar]=useState(false)
  const [evidencia,setEvidencia]=useState(''),[hasta,setHasta]=useState(()=>fechaLocal(new Date(Date.now()+86400000).toISOString()))
  const [error,setError]=useState<unknown>(null),[busy,setBusy]=useState(false)
  const consulta=useQuery({queryKey:['inspeccion',id],queryFn:()=>request<Schema['InspeccionAlmacen']>(`/almacenes/${id}/inspeccion`).catch(e=>{if(e instanceof ApiError && e.status===404)return null;throw e})})
  async function guardar() {
    setError(null);setBusy(true)
    try {
      await write(`/almacenes/${id}/inspecciones`,{revision_almacen:revision,fecha:new Date().toISOString(),vigente_hasta:new Date(hasta).toISOString(),evidencia,observaciones:convertir(datos)})
      setEditar(false);setDatos({})
      await Promise.all([['inspeccion',id],['almacenes-lotes'],['unidades'],['inicio'],['vigencia']].map(queryKey=>qc.invalidateQueries({queryKey})))
    } catch(e){setError(e)} finally {setBusy(false)}
  }
  return <div className="stack">
    <h3>Inspección compartida del almacén</h3>
    <ErrorMessage error={error || consulta.error}/>
    {consulta.data ? <><p>Registrada {fecha(consulta.data.fecha)} · válida hasta {fecha(consulta.data.vigente_hasta)}.</p><p>{consulta.data.evidencia}</p></> : <p>No hay una inspección vigente para reutilizar en las unidades de este almacén.</p>}
    <p className="muted">Solo se comparte infraestructura e higiene ambiental. Las mediciones y los hallazgos del grano se comprueban por lote. Una nueva inspección cambia la revisión del almacén y exige reevaluar autorizaciones anteriores.</p>
    <button onClick={()=>setEditar(v=>!v)}>{editar?'Cerrar captura de inspección':'Registrar inspección del almacén'}</button>
    {editar && <><p>Vigencia máxima de siete días: política del prototipo, no plazo agronómico certificado. Si cambian las condiciones, actualiza el almacén y registra otra inspección. Los campos omitidos quedan pendientes.</p>
      <Field label="Evidencia de inspección del almacén"><input value={evidencia} onChange={e=>setEvidencia(e.target.value)}/></Field>
      <Field label="Inspección válida hasta"><input type="datetime-local" value={hasta} onChange={e=>setHasta(e.target.value)}/></Field>
      <Captura filtro={campos} datos={datos} onChange={setDatos}/>
      {consulta.data && <button onClick={()=>setDatos(desdeObservaciones(consulta.data!.observaciones))}>Recuperar inspección anterior como referencia</button>}
      <button className="primary" disabled={busy || !evidencia.trim() || !Object.keys(datos).length} onClick={()=>void guardar()}>Guardar inspección compartida</button>
    </>}
  </div>
}
