import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { iniciales, nombre, request, write, type Schema } from '../api/client'
import Panel, { Badge, ConfirmDialog, Empty, ErrorMessage, Field, PageHeader, SkeletonPage } from '../components/Shared'
import { useToast } from '../components/Toast'

export default function Configuracion() {
  const qc=useQueryClient(),perfil=qc.getQueryData<Schema['Perfil']>(['perfil']),avisar=useToast()
  const admin=!!perfil?.roles.includes('ADMINISTRADOR')
  const [tecnico,setTecnico]=useState(''),[recurso,setRecurso]=useState(''),[error,setError]=useState<unknown>(null),[busy,setBusy]=useState(false)
  const [revocar,setRevocar]=useState<Schema['AsignacionTecnica']|null>(null)
  const q=useQuery({queryKey:['administracion'],enabled:admin,queryFn:()=>request<Schema['Administracion']>('/administracion/asignaciones')})
  async function guardar(a:Schema['AsignacionTecnica']) {
    setError(null);setBusy(true)
    try {
      await write('/administracion/asignaciones',a);await qc.invalidateQueries({queryKey:['administracion']})
      avisar(a.vigente?'Asignación guardada':'Asignación revocada', a.vigente?'El técnico ya puede ver ese recurso.':'El técnico deja de ver ese recurso.')
      setRevocar(null)
    } catch(e){setError(e)} finally {setBusy(false)}
  }
  if(q.isLoading)return <SkeletonPage label="Cargando configuración…"/>
  const nombreRecurso=(id:string)=>q.data?.recursos.find(r=>r.id===id)?.nombre??id
  const nombreTecnico=(id:string)=>q.data?.tecnicos.find(t=>t.id===id)?.nombre??id
  return <div className="stack"><PageHeader eyebrow="Cuenta y accesos" title="Configuración" />
    <Panel title="Tu función en el sistema">
      <div className="list-item" style={{marginBottom:16}}><span className="avatar" aria-hidden="true">{iniciales(perfil?.nombre||'')}</span><div><strong>{perfil?.nombre}</strong><span className="actions" style={{gap:4}}>{perfil?.roles.map(r=><span key={r} className="badge">{nombre(r)}</span>)}</span></div></div>
      <p>Productor: captura y seguimiento de sus lotes. Técnico: evaluación y resolución en unidades asignadas. Administrador: asignaciones. Ingeniero del conocimiento: modelo y versiones Mamdani.</p><p className="muted">La configuración administrativa no sustituye una evaluación ni modifica el conocimiento activo. Los roles se otorgan mediante el procedimiento administrativo documentado.</p></Panel>
    <ErrorMessage error={error||q.error} onRetry={q.error?()=>void q.refetch():undefined}/>
    {admin && q.data && <Panel title="Asignaciones de técnicos">
      <p className="muted">Asigna o revoca acceso a un almacén o lote. Este permiso no da al administrador acceso a las observaciones ni a las evaluaciones de producción.</p>
      <div className="form-grid"><Field label="Técnico a asignar"><select value={tecnico} onChange={e=>setTecnico(e.target.value)}><option value="">Seleccionar</option>{q.data.tecnicos.map(t=><option key={t.id} value={t.id}>{t.nombre}</option>)}</select></Field><Field label="Recurso a asignar"><select value={recurso} onChange={e=>setRecurso(e.target.value)}><option value="">Seleccionar</option>{q.data.recursos.map(r=><option key={`${r.tipo}:${r.id}`} value={`${r.tipo}:${r.id}`}>{nombre(r.tipo)} · {r.nombre}</option>)}</select></Field>
        <div className="field" style={{alignSelf:'end'}}><button className="primary" disabled={busy||!tecnico||!recurso} onClick={()=>{const [tipo,id_recurso]=recurso.split(':');void guardar({id_tecnico:tecnico,id_recurso,tipo:tipo as 'ALMACEN'|'LOTE',vigente:true})}}>Guardar asignación</button></div></div>
      {q.data.asignaciones.length ? <div className="table-scroll" style={{marginTop:20}}><table className="table-cards"><thead><tr><th>Técnico</th><th>Recurso</th><th>Estado</th><th><span className="sr-only">Acción</span></th></tr></thead><tbody>{q.data.asignaciones.map(a=><tr key={`${a.id_tecnico}:${a.tipo}:${a.id_recurso}`}>
        <td data-label="Técnico">{nombreTecnico(a.id_tecnico)}</td><td data-label="Recurso">{nombreRecurso(a.id_recurso)} · {nombre(a.tipo)}</td><td data-label="Estado"><Badge tono={a.vigente?'ok':''}>{a.vigente?'Vigente':'Revocada'}</Badge></td>
        <td data-label=""><div className="actions end"><button className={`btn-sm${a.vigente?' btn-danger':''}`} disabled={busy} onClick={()=>a.vigente?setRevocar(a):void guardar({...a,vigente:true})}>{a.vigente?'Revocar':'Restablecer'}</button></div></td></tr>)}</tbody></table></div>
        : <Empty>Aún no hay asignaciones registradas.</Empty>}
    </Panel>}
    <ConfirmDialog open={!!revocar} title="¿Revocar la asignación?" confirmLabel="Revocar acceso" danger busy={busy} onCancel={()=>setRevocar(null)} onConfirm={()=>revocar&&void guardar({...revocar,vigente:false})}>
      {revocar&&<p>{nombreTecnico(revocar.id_tecnico)} dejará de ver {nombreRecurso(revocar.id_recurso)} y sus unidades. Puedes restablecerla después.</p>}
    </ConfirmDialog>
  </div>
}
