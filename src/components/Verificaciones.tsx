import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, request, fecha, type Schema } from '../api/client'
import campos from '../campos.json'
import Captura, { desdeObservaciones, type CapturaDatos } from './Captura'

const grupos = [
  {pasos:[3], titulo:'Inspección del grano: plagas, deterioro y calidad'},
  {pasos:[4,7], titulo:'Recipiente, estiba y accesos'},
  {pasos:[6], titulo:'Infraestructura y entorno'},
  {pasos:[8], titulo:'Identidad, trazabilidad y movimientos'},
  {pasos:[9], titulo:'Sustancias, prevención y vencimiento'},
  {pasos:[5], titulo:'Inspecciones y controles documentados'},
]

export default function Verificaciones({datos,historicos,onChange,idAlmacen}: {datos:CapturaDatos;historicos:CapturaDatos;onChange:(d:CapturaDatos)=>void;idAlmacen?:string}) {
  const [revisarCompartidos,setRevisarCompartidos] = useState(false)
  const inspeccion = useQuery({queryKey:['inspeccion',idAlmacen],enabled:!!idAlmacen,queryFn:()=>request<Schema['InspeccionAlmacen']>(`/almacenes/${idAlmacen}/inspeccion`).catch(e=>{if(e instanceof ApiError && e.status===404)return null;throw e})})
  const compartidos = new Set(inspeccion.data?.observaciones.filter(o=>o.captura==='APORTADO').map(o=>o.campo) ?? [])
  const referencias = {...desdeObservaciones(inspeccion.data?.observaciones ?? []),...historicos}
  const efectivos = {...referencias,...datos}
  return <div className="stack">
    <p>Las respuestas sanitarias también participan en los antecedentes de la decisión Mamdani. «No se sabe» no significa «No». Puedes evaluar información parcial si detectas un hallazgo crítico.</p>
    {inspeccion.error && <p className="message error">No se pudo consultar la inspección del almacén. Las comprobaciones permanecen disponibles.</p>}
    {inspeccion.data && <div className="message"><strong>Inspección de almacén disponible</strong><p>Fecha: {fecha(inspeccion.data.fecha)} · válida hasta {fecha(inspeccion.data.vigente_hasta)}. El servidor comprobará revisión, alcance y eventos antes de reutilizarla.</p><p>{inspeccion.data.evidencia}</p><label className="check"><input type="checkbox" checked={revisarCompartidos} onChange={e=>setRevisarCompartidos(e.target.checked)}/>Revisar o reemplazar comprobaciones compartidas</label></div>}
    <label className="check"><input type="checkbox" checked={revisarCompartidos} onChange={e=>setRevisarCompartidos(e.target.checked)}/>Mostrar todas las comprobaciones condicionales y compartidas</label>
    {grupos.map((g,i)=>{
      const filtro = Object.entries(campos).filter(([c,d])=>g.pasos.includes(d.paso) && c!=='granos_defectuosos' &&
        (revisarCompartidos || !compartidos.has(c) || !!efectivos[c]) &&
        (c!=='fecha_vencimiento_producto' || efectivos.vencimiento_aplicable?.valor==='true' || revisarCompartidos) &&
        (c!=='separacion_cuarentena_verificada' || !!efectivos[c] || revisarCompartidos)).map(([c])=>c)
      return <details className="capture-group" key={g.titulo} open={i===0}><summary>{g.titulo}</summary><Captura datos={datos} historicos={referencias} onChange={onChange} filtro={filtro}/></details>
    })}
    <p className="muted">Los campos condicionales no visibles conservan sus observaciones; no se rellenan como favorables. Si la evidencia no basta, el resultado indicará qué completar.</p>
  </div>
}
