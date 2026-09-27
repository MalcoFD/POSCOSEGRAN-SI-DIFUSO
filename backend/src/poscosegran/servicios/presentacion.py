"""Conversión de filas persistidas a los esquemas del contrato."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import (
    AccionRequerida,
    Activacion,
    Pertenencia,
    SalidaDifusa,
    Almacen,
    DatoPendiente,
    Estimacion,
    Evaluacion,
    Motivo,
    MotivoEvidencia,
    MotivoFuente,
    Observacion,
    ObservacionAplicada,
    Unidad,
)
from ..esquemas import contrato as api
from ..sistema_experto.base_hechos import Activacion as ActivacionMotor
from ..sistema_experto.difuso import InferenciaDifusa as InferenciaMotor
from . import observaciones as obs


def _numero(valor: object) -> float | bool | str | None:
    if valor is None or isinstance(valor, (bool, str)):
        return valor
    return float(valor)  


def almacen(fila: Almacen) -> api.Almacen:
    return api.Almacen.model_validate(dict(
        id=fila.id,
        nombre=fila.nombre,
        ubicacion=fila.ubicacion,
        clima_calido=fila.clima_calido,
        fundamento_clima=fila.fundamento_clima,
        revision=fila.revision,
        creado_en=fila.creado_en,
    ))


def unidad(fila: Unidad, revision_almacen: int) -> api.Unidad:
    return api.Unidad.model_validate(dict(
        id=fila.id,
        id_lote=fila.id_lote,
        id_almacen=fila.id_almacen,
        id_recipiente=fila.id_recipiente,
        nombre_recipiente=fila.nombre_recipiente,
        tipo_almacenamiento=fila.tipo_almacenamiento,
        revision=fila.revision,
        revision_almacen=revision_almacen,
        id_evaluacion_actual=fila.id_evaluacion_actual,
        creado_en=fila.creado_en,
    ))


def evaluacion(sesion: Session, fila: Evaluacion) -> api.Evaluacion:
    motivos: list[api.Motivo] = []
    for motivo in sesion.scalars(
        sa.select(Motivo).where(Motivo.id_evaluacion == fila.id).order_by(Motivo.orden)
    ):
        evidencias = [
            api.EvidenciaMotivo.model_validate(dict(
                campo=prueba.campo,
                valor_observado=_numero(
                    prueba.valor_numero
                    if prueba.valor_numero is not None
                    else prueba.valor_booleano
                    if prueba.valor_booleano is not None
                    else prueba.valor_texto
                ),
                unidad=prueba.unidad_dato,
                fecha_observacion=prueba.fecha_observacion,
                operador=prueba.operador,
                umbral=_numero(
                    prueba.umbral_numero
                    if prueba.umbral_numero is not None
                    else prueba.umbral_booleano
                    if prueba.umbral_booleano is not None
                    else prueba.umbral_texto
                ),
                termino=prueba.termino,
                grado=float(prueba.grado) if prueba.grado is not None else None,
            ))
            for prueba in sesion.scalars(
                sa.select(MotivoEvidencia)
                .where(MotivoEvidencia.id_motivo == motivo.id)
                .order_by(MotivoEvidencia.orden)
            )
        ]
        fuentes = [
            api.FuenteRef.model_validate(dict(id_fuente=ref.id_fuente, localizador=ref.localizador))
            for ref in sesion.scalars(
                sa.select(MotivoFuente).where(MotivoFuente.id_motivo == motivo.id)
            )
        ]
        motivos.append(
            api.Motivo.model_validate(dict(
                id=motivo.codigo,
                regla=motivo.regla,
                mensaje=motivo.mensaje,
                evidencias=evidencias,
                fuentes=fuentes,
                fundamento=motivo.fundamento,
                grado_activacion=float(motivo.grado_activacion),
            ))
        )

    acciones = [
        api.Accion.model_validate(dict(
            codigo=accion.codigo,
            descripcion=accion.descripcion,
            responsable_requerido=accion.responsable_requerido,
            id_incidencia=accion.id_incidencia,
        ))
        for accion in sesion.scalars(
            sa.select(AccionRequerida)
            .where(AccionRequerida.id_evaluacion == fila.id)
            .order_by(AccionRequerida.orden)
        )
    ]
    pendientes = [
        api.DatoPendiente.model_validate(dict(campo=dato.campo, motivo=dato.motivo, paso=dato.paso))
        for dato in sesion.scalars(
            sa.select(DatoPendiente)
            .where(DatoPendiente.id_evaluacion == fila.id)
            .order_by(DatoPendiente.orden)
        )
    ]
    estimaciones = [
        api.Estimacion.model_validate(dict(
            tipo=item.tipo,
            descripcion=item.descripcion,
            campos=list(item.campos),
            id_tabla=item.id_tabla,
        ))
        for item in sesion.scalars(
            sa.select(Estimacion)
            .where(Estimacion.id_evaluacion == fila.id)
            .order_by(Estimacion.orden)
        )
    ]
    aplicadas = [
        obs.a_validada(observacion)
        for observacion in sesion.scalars(
            sa.select(Observacion)
            .join(ObservacionAplicada, ObservacionAplicada.id_observacion == Observacion.id)
            .where(ObservacionAplicada.id_evaluacion == fila.id)
            .order_by(ObservacionAplicada.orden)
        )
    ]

    if "_observaciones_aplicadas" in fila.entrada_efectiva:
        aplicadas = [api.ObservacionValidada.model_validate(item)
                     for item in fila.entrada_efectiva["_observaciones_aplicadas"]]
    if fila.celda_tabla_id:
        assert fila.celda_humedad_fila is not None and fila.celda_temperatura_columna_f is not None
    celda = (
        api.CeldaTabla.model_validate(dict(
            id_tabla=fila.celda_tabla_id,
            humedad_fila=_numero(fila.celda_humedad_fila),
            temperatura_columna_f=_numero(fila.celda_temperatura_columna_f),
            dias_referencia=fila.celda_dias_referencia,
        ))
        if fila.celda_tabla_id
        else None
    )

    return api.Evaluacion.model_validate(dict(
        id=fila.id,
        id_unidad=fila.id_unidad,
        id_lote=fila.id_lote,
        id_recipiente=fila.id_recipiente,
        id_almacen=fila.id_almacen,
        fecha_evaluacion=fila.fecha_evaluacion,
        fase=fila.fase,
        decision_final=fila.decision_final,
        rama_r30=fila.rama_r30,
        motivos=motivos,
        acciones_requeridas=acciones,
        datos_pendientes=pendientes,
        estimaciones_y_sustituciones=estimaciones,
        reglas_activadas=list(fila.reglas_activadas),
        observaciones_aplicadas=aplicadas,
        calculos_tiempo=api.CalculosTiempo.model_validate(dict(
            vida_consumida=_numero(fila.vida_consumida),
            vida_minima_documentada=_numero(fila.vida_minima_documentada),
            vida_proyectada=_numero(fila.vida_proyectada),
            tiempo_referencia_actual=fila.tiempo_referencia_actual,
            celda_tabla=celda,
        )),
        fecha_proximo_control=fila.fecha_proximo_control,
        fecha_vencimiento_autorizacion=fila.fecha_vencimiento_autorizacion,
        version_base=fila.version_base,
        version_parametros=fila.version_parametros,
        version_motor=fila.version_motor,
        inferencia=inferencia(sesion, fila),
    ))


def inferencia_del_motor(
    resultado: InferenciaMotor | None, traza: Sequence[ActivacionMotor]
) -> api.InferenciaDifusa | None:
    """Convierte la inferencia recién calculada por el motor al contrato."""
    if resultado is None:
        return None
    return api.InferenciaDifusa.model_validate(dict(
        pertenencias=[
            api.PertenenciaDifusa(
                variable=p.variable, termino=p.termino, valor=p.valor, unidad=p.unidad, grado=p.grado
            )
            for p in resultado.pertenencias
        ],
        activaciones=[
            api.ActivacionDifusa(
                orden=a.orden, produccion=a.produccion, regla=a.regla, etapa=a.etapa, pasada=a.pasada,
                grado_inf=a.grado, grado_sup=a.grado_sup, hallazgo=a.hallazgo,
                terminos_salida=list(a.terminos_salida),
            )
            for a in traza
        ],
        salida=api.SalidaDifusa(
            variable=resultado.salida.variable,
            metodo="CENTROIDE",
            alturas=[api.AlturaSalida(termino=t, altura=h) for t, h in resultado.salida.alturas],
            indice=resultado.salida.indice,
            banda=resultado.salida.banda,
            decision_indice=resultado.salida.decision_indice,
        ),
        origen_decision=resultado.origen_decision,
        borrosidad=resultado.borrosidad,
    ))


def inferencia(sesion: Session, fila: Evaluacion) -> api.InferenciaDifusa | None:
    """Reconstruye la inferencia difusa persistida; None en evaluaciones nítidas."""
    if fila.origen_decision is None or fila.metodo_defuzzificacion is None:
        return None
    pertenencias = [
        api.PertenenciaDifusa(
            variable=p.variable,
            termino=p.termino,
            valor=float(p.valor_nitido) if p.valor_nitido is not None else None,
            unidad=p.unidad,
            grado=float(p.grado),
        )
        for p in sesion.scalars(
            sa.select(Pertenencia)
            .where(Pertenencia.id_evaluacion == fila.id)
            .order_by(Pertenencia.variable, Pertenencia.termino)
        )
    ]
    activaciones = [
        api.ActivacionDifusa(
            orden=a.orden,
            produccion=a.produccion,
            regla=a.regla,
            etapa=a.etapa,
            pasada=a.pasada,
            grado_inf=float(a.grado_inf),
            grado_sup=float(a.grado_sup),
            hallazgo=a.hallazgo,
            terminos_salida=list(a.terminos_salida),
        )
        for a in sesion.scalars(
            sa.select(Activacion).where(Activacion.id_evaluacion == fila.id).order_by(Activacion.orden)
        )
    ]
    salidas = list(
        sesion.scalars(
            sa.select(SalidaDifusa).where(SalidaDifusa.id_evaluacion == fila.id).order_by(SalidaDifusa.termino)
        )
    )
    variable = salidas[0].variable if salidas else "severidad"
    return api.InferenciaDifusa.model_validate(dict(
        pertenencias=pertenencias,
        activaciones=activaciones,
        salida=api.SalidaDifusa(
            variable=variable,
            metodo="CENTROIDE",
            alturas=[api.AlturaSalida(termino=s.termino, altura=float(s.altura)) for s in salidas],
            indice=float(fila.indice_severidad) if fila.indice_severidad is not None else None,
            banda=fila.banda_severidad,
            decision_indice=None,
        ),
        origen_decision=fila.origen_decision,
        borrosidad=float(fila.borrosidad) if fila.borrosidad is not None else None,
    ))
