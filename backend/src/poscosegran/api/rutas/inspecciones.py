"""Inspecciones de almacén compartidas con sus unidades autorizadas."""
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException

from ...db.modelos import Almacen, InspeccionAlmacen
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import exigir_acceso_almacen, RecursoInaccesible
from ...servicios import auditoria, concurrencia, observaciones
from ...servicios.inspecciones import CAMPOS_ALMACEN, vigente
from ..dependencias import ClaveIdempotencia, completar, reservar

enrutador = APIRouter(prefix='/api/v1', tags=['inspecciones de almacén'])


def salida(fila: InspeccionAlmacen) -> api.InspeccionAlmacen:
    return api.InspeccionAlmacen.model_validate({k: getattr(fila, k) for k in api.InspeccionAlmacen.model_fields})


@enrutador.get('/almacenes/{id_almacen}/inspeccion', response_model=api.InspeccionAlmacen)
def consultar(id_almacen: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep) -> api.InspeccionAlmacen:
    exigir_acceso_almacen(sesion, identidad, id_almacen)
    almacen = sesion.get(Almacen, id_almacen)
    assert almacen is not None
    fila = vigente(sesion, almacen, datetime.now(UTC))
    if fila is None:
        raise RecursoInaccesible(str(id_almacen))
    return salida(fila)


@enrutador.post('/almacenes/{id_almacen}/inspecciones', response_model=api.InspeccionAlmacen, status_code=201)
def registrar(id_almacen: uuid.UUID, entrada: api.InspeccionAlmacenEntrada, sesion: SesionDep,
              identidad: IdentidadDep, idempotency_key: ClaveIdempotencia = None) -> api.InspeccionAlmacen:
    exigir_acceso_almacen(sesion, identidad, id_almacen, escritura=True)
    repetida = reservar(sesion, identidad, idempotency_key, 'POST', f'/almacenes/{id_almacen}/inspecciones', entrada.model_dump(mode='json'))
    if repetida is not None and repetida.cuerpo is not None:
        return api.InspeccionAlmacen.model_validate(repetida.cuerpo)
    almacen = sesion.get(Almacen, id_almacen, with_for_update=True)
    assert almacen is not None
    concurrencia.exigir_revision(almacen.revision, entrada.revision_almacen)
    ahora = datetime.now(UTC)
    if entrada.fecha > ahora or entrada.vigente_hasta <= ahora or entrada.vigente_hasta > entrada.fecha + timedelta(days=7):
        raise HTTPException(422, 'La inspección debe ser actual y su vigencia máxima es siete días (política del prototipo).')
    if not entrada.observaciones or len({o.campo for o in entrada.observaciones}) != len(entrada.observaciones):
        raise HTTPException(422, 'Indique observaciones sin campos repetidos.')
    for o in entrada.observaciones:
        if o.campo not in CAMPOS_ALMACEN or observaciones.validar(o)[0] == 'INVALIDO':
            raise HTTPException(422, f'Campo no compartible o inválido: {o.campo}')
        if o.fecha_observacion and o.fecha_observacion > entrada.fecha:
            raise HTTPException(422, 'Una observación no puede ser posterior a la inspección.')
    almacen.revision += 1
    fila = InspeccionAlmacen(id_almacen=id_almacen, id_responsable=identidad.id,
                            revision_almacen=almacen.revision, fecha=entrada.fecha,
                            vigente_hasta=entrada.vigente_hasta, evidencia=entrada.evidencia,
                            observaciones=[o.model_dump(mode='json') for o in entrada.observaciones])
    sesion.add(fila)
    sesion.flush()
    respuesta = salida(fila)
    auditoria.registrar(sesion, identidad=identidad, accion='REGISTRAR_INSPECCION_ALMACEN', recurso_tipo='almacen',
                       recurso_id=id_almacen, revision_resultante=almacen.revision)
    completar(sesion, identidad, idempotency_key, 201, fila.id, respuesta.model_dump(mode='json'))
    return respuesta
