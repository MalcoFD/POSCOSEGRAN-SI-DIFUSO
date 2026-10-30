"""Inferencia Mamdani directa: una matriz por modalidad y un único centroide."""

from __future__ import annotations
from datetime import datetime, timedelta
import math
from typing import Any
from ..dominio.hechos import Accion, Instantanea, Motivo, Pendiente
from ..dominio.valores import D, F, V
from ..inferencia.base_conocimiento import BaseConocimiento
from ..inferencia.base_hechos import Activacion
from ..inferencia.calculos import CalculosTiempo
from ..inferencia.motor import Resultado
from .defuzzificacion import centroide
from .pertenencia import pertenencia
from .reglas import activacion

VERSION_MOTOR = "4.0.0-matricial"


class MotorDifuso:
    version = VERSION_MOTOR

    def __init__(self, base: BaseConocimiento) -> None:
        self.base = base

    def evaluar(self, instantanea: Instantanea) -> Resultado:
        modelo = self.base.contenido["operativa"]["difuso"]
        modalidad = (
            instantanea.tipo_almacenamiento.value if instantanea.tipo_almacenamiento else None
        )
        matriz = modelo["matrices"].get(modalidad)
        pendientes: list[Pendiente] = []
        entradas: dict[str, Any] = {}
        grados: dict[str, dict[str, float]] = {}
        if matriz is None:
            pendientes.append(
                Pendiente("tipo_almacenamiento", "Seleccionar una modalidad de almacenamiento.", 1)
            )
        aplicables = matriz["entradas"] if matriz else []
        vigencia_horas = modelo["politica"]["vigencia_medicion_horas"]
        for campo, definicion in modelo["entradas"].items():
            dato = instantanea.datos[campo]
            valor: Any = (
                dato.texto
                if definicion["tipo"] == "CATEGORICA"
                else (float(dato.numero) if dato.numero is not None else None)
            )
            estado = "CALCULADO"
            mu: dict[str, float] = {}
            motivo = ""
            if campo not in aplicables:
                estado = "NO_APLICA"
            elif not dato.utilizable or valor is None:
                estado, motivo = (
                    "DESCONOCIDO",
                    "Aportar un dato válido; desconocido no equivale a cero.",
                )
            elif dato.fecha_observacion is None or not dato.metodo:
                estado, motivo = "INVALIDO", "Registrar fecha y método de la observación."
            elif dato.fecha_observacion > instantanea.fecha_evaluacion:
                estado, motivo = (
                    "INVALIDO",
                    "La observación no puede ser posterior a la evaluación.",
                )
            elif (
                instantanea.fecha_evaluacion - dato.fecha_observacion
            ).total_seconds() > vigencia_horas * 3600:
                estado, motivo = (
                    "VENCIDO",
                    "La observación supera la ventana documentada de siete días; actualizarla.",
                )
            elif definicion["tipo"] == "CATEGORICA":
                if valor not in definicion["conjuntos"]:
                    estado, motivo = (
                        "INVALIDO",
                        "Seleccionar uno de los cuatro estados del protocolo.",
                    )
                elif not (dato.evidencia or "").strip():
                    estado, motivo = (
                        "INVALIDO",
                        "Describir la inspección, muestra y hallazgos; también cuando no se observen anomalías.",
                    )
                else:
                    mu = {k: float(k == valor) for k in definicion["conjuntos"]}
            elif (
                not math.isfinite(valor)
                or not definicion["dominio"][0] <= valor <= definicion["dominio"][1]
            ):
                estado, motivo = (
                    "FUERA_DE_DOMINIO",
                    "Medición fuera del dominio; revisar instrumento y unidad.",
                )
            elif campo == "humedad_grano" and dato.metodo not in {"INSTRUMENTAL", "LABORATORIO"}:
                estado, motivo = (
                    "INVALIDO",
                    "La humedad exige medición instrumental o de laboratorio.",
                )
            else:
                mu = {k: pertenencia(valor, p) for k, p in definicion["conjuntos"].items()}
            if motivo:
                pendientes.append(
                    Pendiente(campo, motivo, 3 if definicion["tipo"] == "CATEGORICA" else 2)
                )
            grados[campo] = mu
            entradas[campo] = {
                "id": campo,
                "nombre": definicion["nombre"],
                "valor": valor,
                "unidad": definicion["unidad"],
                "estado": estado,
                "pertenencias": mu,
                "definicion": definicion,
                "conjuntos": definicion["conjuntos"],
                "dominio": definicion["dominio"],
                "fuentes": definicion["fuentes"],
                "fecha_observacion": dato.fecha_observacion.isoformat()
                if dato.fecha_observacion
                else None,
                "metodo": dato.metodo,
                "evidencia": dato.evidencia,
                "procedencia": dato.procedencia.value,
            }
        if modalidad == "HERMETICO":
            for campo, admitidos in [
                ("estado_barrera", {"INTEGRA"}),
                ("procedimiento_interno", {"SENSOR_INTERNO", "INSPECCION_PREVIA_SELLADO"}),
            ]:
                dato = instantanea.datos[campo]
                vigente = (
                    dato.fecha_observacion is not None
                    and 0
                    <= (instantanea.fecha_evaluacion - dato.fecha_observacion).total_seconds()
                    <= vigencia_horas * 3600
                )
                if (
                    not dato.utilizable
                    or dato.texto not in admitidos
                    or not vigente
                    or not dato.metodo
                    or not dato.evidencia
                ):
                    pendientes.append(
                        Pendiente(
                            campo,
                            "Documentar barrera íntegra y procedimiento interno vigente. Una barrera no íntegra exige reevaluar como no hermético; no se estima humedad interna con HR externa.",
                            3,
                        )
                    )
        reglas: list[dict[str, Any]] = []
        if matriz:
            for r in matriz["reglas"]:
                alfa = activacion(r["si"], grados) if not pendientes else 0.0
                reglas.append(
                    {
                        **r,
                        "antecedente": r["si"],
                        "alfa": alfa,
                        "consecuente": r["entonces"],
                        "puntos_salida": modelo["salidas"][r["entonces"]],
                    }
                )
        calculo = (
            centroide([(r["puntos_salida"], r["alfa"]) for r in reglas]) if not pendientes else None
        )
        if matriz and not pendientes and calculo is None:
            raise ValueError(
                "Matriz Mamdani sin cobertura numérica: el modelo no produce un resultado válido."
            )
        indice, area, curva = calculo if calculo else (None, None, [])
        clase = next(
            (c for c in modelo["clasificacion"] if indice is not None and indice < c["hasta"]), None
        )
        decision = clase["decision"] if clase else "SIN_CONCLUSION_AUTOMATICA"
        recomendacion = (
            clase["recomendacion"]
            if clase
            else "Completar o corregir los datos de entrada; no se ha calculado un índice."
        )
        activas = [r for r in reglas if r["alfa"] > 0]
        motivos = tuple(
            Motivo(
                id=r["id"] + ":MAMDANI",
                regla=r["id"],
                mensaje=f"Activación {r['alfa']:.6f}; consecuente {r['entonces']}.",
                fuentes=self.base.fuentes_de(r["id"]),
                fundamento="MIXTO",
            )
            for r in activas
        )
        traza = tuple(
            Activacion(
                i,
                "MAMDANI",
                1,
                r["id"],
                r["id"],
                r["entonces"],
                tuple(f"{h['entrada']}={h['conjunto']}" for h in r["si"]["todos"]),
                (),
            )
            for i, r in enumerate(activas, 1)
        )
        dias = clase["control_dias"] if clase else None
        proximo = instantanea.fecha_evaluacion + timedelta(days=dias) if dias else None
        autorizada = decision in self.base.decisiones_autorizadas
        # La vigencia de una recomendación nunca supera la de las mediciones aplicadas.
        vencimiento: datetime | None = None
        if autorizada and proximo:
            limites = [proximo]
            for campo in [
                *aplicables,
                *(["estado_barrera", "procedimiento_interno"] if modalidad == "HERMETICO" else []),
            ]:
                fecha = instantanea.datos[campo].fecha_observacion
                assert fecha is not None
                limites.append(fecha + timedelta(hours=vigencia_horas))
            vencimiento = min(limites)
            proximo = min(proximo, vencimiento)
        informe = {
            "tipo": "MAMDANI_MATRICIAL_DIRECTO",
            "modalidad": modalidad,
            "matriz": matriz["id"] if matriz else None,
            "estado": "CALCULADO" if calculo else "DATOS_PENDIENTES",
            "entradas": entradas,
            "reglas": reglas,
            "centroide": indice,
            "area": area,
            "curva": curva,
            "clasificacion": modelo["clasificacion"],
            "salidas": modelo["salidas"],
            "decision": decision,
            "recomendacion": recomendacion,
            "fundamento": modelo["fundamento"],
            "operadores": modelo["operadores"],
        }
        solicitudes = (
            {"CUARENTENA_SOLICITADA": tuple(r["id"] for r in activas)}
            if decision == "CUARENTENA"
            else {}
        )
        iniciales = tuple(
            (
                k,
                (
                    float(d.numero)
                    if d.numero is not None
                    else d.texto
                    if d.texto is not None
                    else d.valor
                ),
                d.procedencia.value,
            )
            for k, d in instantanea.datos.datos.items()
            if k in aplicables or k in {"estado_barrera", "procedimiento_interno"}
        )
        return Resultado(
            decision_final=decision,
            motivos=motivos,
            acciones_requeridas=(
                Accion(
                    decision,
                    recomendacion,
                    "TECNICO"
                    if decision in {"CUARENTENA", "SUSPENDER_ALMACENAMIENTO"}
                    else "PRODUCTOR",
                ),
            ),
            datos_pendientes=tuple(pendientes),
            estimaciones=(),
            reglas_activadas=tuple(r["id"] for r in activas),
            calculos=CalculosTiempo(),
            fecha_proximo_control=proximo,
            fecha_vencimiento_autorizacion=vencimiento,
            solicitudes=solicitudes,
            riesgo_activo=D if not calculo else F if decision == "AUTORIZAR_ALMACENAMIENTO" else V,
            version_base=self.base.version_base,
            version_parametros=self.base.version_parametros,
            version_motor=self.version,
            hash_base=self.base.hash,
            traza=traza,
            hechos_inferidos=(),
            hechos_iniciales=iniciales,
            no_aplicables=("hr_almacen",) if modalidad == "HERMETICO" else (),
            difuso={
                "tipo": "MAMDANI_TIPO_1",
                "estructura": "MATRICIAL_DIRECTA",
                "version": self.version,
                "total_reglas": 320,
                "operadores": modelo["operadores"],
                "decision": informe,
                "nota": "Índice de intervención del prototipo; no es probabilidad ni certificación de inocuidad.",
            },
        )
