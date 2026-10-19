"""Administración de asignaciones; no concede acceso a evaluaciones de producción."""
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi import APIRouter, HTTPException

from ...db.modelos import Usuario, UsuarioRol, Almacen, Lote, AsignacionAlmacen, AsignacionLote
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import AccesoDenegado
from ...servicios import auditoria
from ..dependencias import ClaveIdempotencia, reservar, completar

enrutador = APIRouter(prefix='/api/v1/administracion', tags=['administración'])


@enrutador.get('/asignaciones', response_model=api.Administracion)
def consultar(sesion: SesionDep, identidad: IdentidadDep) -> api.Administracion:
    if not identidad.es_administrador:
        raise AccesoDenegado('Se requiere administrador')
    tecnicos = sesion.scalars(sa.select(Usuario).join(UsuarioRol, UsuarioRol.id_usuario == Usuario.id)
                              .where(UsuarioRol.rol == 'TECNICO', Usuario.activo.is_(True))).all()
    recursos = [api.RecursoAsignable(id=a.id, nombre=a.nombre, tipo='ALMACEN') for a in sesion.scalars(sa.select(Almacen))]
    recursos += [api.RecursoAsignable(id=lote.id, nombre=lote.codigo, tipo='LOTE') for lote in sesion.scalars(sa.select(Lote))]
    asignaciones = [api.AsignacionTecnica(id_tecnico=a.id_tecnico,id_recurso=a.id_almacen,tipo='ALMACEN',vigente=a.vigente)
                   for a in sesion.scalars(sa.select(AsignacionAlmacen))]
    asignaciones += [api.AsignacionTecnica(id_tecnico=a.id_tecnico,id_recurso=a.id_lote,tipo='LOTE',vigente=a.vigente)
                    for a in sesion.scalars(sa.select(AsignacionLote))]
    return api.Administracion(tecnicos=[api.TecnicoAsignable(id=t.id,nombre=t.nombre) for t in tecnicos],
                              recursos=recursos, asignaciones=asignaciones)


@enrutador.post('/asignaciones', response_model=api.AsignacionTecnica, status_code=201)
def asignar(entrada: api.AsignacionTecnica, sesion: SesionDep, identidad: IdentidadDep,
            idempotency_key: ClaveIdempotencia = None) -> api.AsignacionTecnica:
    if not identidad.es_administrador:
        raise AccesoDenegado('Se requiere administrador')
    repetida = reservar(sesion,identidad,idempotency_key,'POST','/administracion/asignaciones',entrada.model_dump(mode='json'))
    if repetida is not None and repetida.cuerpo is not None:
        return api.AsignacionTecnica.model_validate(repetida.cuerpo)
    tecnico = sesion.scalar(sa.select(Usuario.id).join(UsuarioRol,UsuarioRol.id_usuario == Usuario.id)
                            .where(Usuario.id == entrada.id_tecnico, Usuario.activo.is_(True), UsuarioRol.rol == 'TECNICO'))
    recurso = sesion.get(Almacen if entrada.tipo == 'ALMACEN' else Lote,entrada.id_recurso)
    if tecnico is None or recurso is None:
        raise HTTPException(422,'Técnico activo o recurso inexistente')
    tabla = AsignacionAlmacen if entrada.tipo == 'ALMACEN' else AsignacionLote
    campo = 'id_almacen' if entrada.tipo == 'ALMACEN' else 'id_lote'
    sesion.execute(insert(tabla).values(id=uuid.uuid4(), id_tecnico=tecnico, **{campo:entrada.id_recurso},
                                       vigente=entrada.vigente, creada_por=identidad.id)
                   .on_conflict_do_update(index_elements=['id_tecnico',campo],set_={'vigente':entrada.vigente}))
    auditoria.registrar(sesion,identidad=identidad,accion='ASIGNACION_TECNICA',recurso_tipo=entrada.tipo,
                       recurso_id=entrada.id_recurso,resumen=entrada.model_dump(mode='json'))
    completar(sesion,identidad,idempotency_key,201,entrada.id_recurso,entrada.model_dump(mode='json'))
    return entrada
