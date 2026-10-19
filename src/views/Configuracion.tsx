import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { request, write, type Schema } from '../api/client'
import Panel, { ErrorMessage, Field, Loading } from '../components/Shared'

export default function Configuracion() {
  const qc=useQueryClient(),perfil=qc.getQueryData<Schema['Perfil']>(['perfil'])
  const admin=!!perfil?.roles.includes('ADMINISTRADOR')
  const [tecnico,setTecnico]=useState(''),[recurso,setRecurso]=useState(''),[error,setError]=useState<unknown>(null),[busy,setBusy]=useState(false)
  const q=useQuery({queryKey:['administracion'],enabled:admin,queryFn:()=>request<Schema['Administracion']>('/administracion/asignaciones')})
  async function guardar(a:Schema['AsignacionTecnica']) {
    setError(null);setBusy(true)
    try {await write('/administracion/asignaciones',a);await qc.invalidateQueries()} catch(e){setError(e)} finally {setBusy(false)}
  }
  if(q.isLoading)return <Loading/>
  return <div className="stack"><h1>Configuración</h1><Panel title="Tu función en el sistema"><p>{perfil?.nombre} · {perfil?.roles.join(' · ')}</p><p>Productor: captura y seguimiento de sus lotes. Técnico: evaluación y resolución en unidades asignadas. Administrador: asignaciones. Ingeniero del conocimiento: modelo y versiones Mamdani.</p><p>La configuración administrativa no sustituye una evaluación ni modifica el conocimiento activo. Los roles se otorgan mediante el procedimiento administrativo documentado.</p></Panel>
    <ErrorMessage error={error||q.error}/>
    {admin && q.data && <Panel title="Asignaciones de técnicos">
      <p>Asigna o revoca acceso a un almacén o lote. Este permiso no da al administrador acceso a las observaciones ni a las evaluaciones de producción.</p>
      <div className="form-grid"><Field label="Técnico a asignar"><select value={tecnico} onChange={e=>setTecnico(e.target.value)}><option value="">Seleccionar</option>{q.data.tecnicos.map(t=><option key={t.id} value={t.id}>{t.nombre}</option>)}</select></Field><Field label="Recurso a asignar"><select value={recurso} onChange={e=>setRecurso(e.target.value)}><option value="">Seleccionar</option>{q.data.recursos.map(r=><option key={`${r.tipo}:${r.id}`} value={`${r.tipo}:${r.id}`}>{r.tipo} · {r.nombre}</option>)}</select></Field></div>
      <button className="primary" disabled={busy||!tecnico||!recurso} onClick={()=>{const [tipo,id_recurso]=recurso.split(':');void guardar({id_tecnico:tecnico,id_recurso,tipo:tipo as 'ALMACEN'|'LOTE',vigente:true})}}>Guardar asignación</button>
      <div className="table-scroll"><table><thead><tr><th>Técnico</th><th>Recurso</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{q.data.asignaciones.map(a=><tr key={`${a.id_tecnico}:${a.tipo}:${a.id_recurso}`}><td>{q.data!.tecnicos.find(t=>t.id===a.id_tecnico)?.nombre??a.id_tecnico}</td><td>{q.data!.recursos.find(r=>r.id===a.id_recurso)?.nombre??a.id_recurso} · {a.tipo}</td><td>{a.vigente?'Vigente':'Revocada'}</td><td><button disabled={busy} onClick={()=>void guardar({...a,vigente:!a.vigente})}>{a.vigente?'Revocar':'Restablecer'}</button></td></tr>)}</tbody></table></div>
    </Panel>}
  </div>
}
