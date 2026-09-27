"""Motor de inferencia genérico: sistema de inferencia difusa tipo Mamdani.

No contiene conocimiento del dominio. Aplica cualquier base de conocimiento
válida siguiendo el ciclo reconocer–actuar, generalizado a grados de verdad:

    1. Fuzzificación: las lecturas numéricas se tratan como singleton y se
       evalúan contra los términos lingüísticos de la base.
    2. Evaluación (Modus Ponens Generalizado): para cada etapa de la agenda, en
       orden, cada producción se activa con α = mín de su antecedente (t-norma de
       Zadeh; las disyunciones internas usan el máximo). El consecuente se afirma
       con grado α; varias producciones que concluyen lo mismo se agregan por
       máximo. Se repite hasta el punto fijo.
    3. Datos exigibles que siguen desconocidos.
    4. Agregación y defuzzificación: cada consecuente de la variable de salida se
       recorta al nivel α (implicación de Mamdani), la unión se toma por máximo y
       el centroide da el índice de severidad nítido.
    5. Resolución jerárquica: la tabla de prioridades R30 se evalúa sobre cortes-α
       (una rama se aplica si el grado cierto de su condición alcanza su corte), y
       el índice solo puede endurecer esa decisión, nunca suavizarla.

Refracción: una producción vuelve a dispararse solo si su grado de activación
aumenta. El sistema es monótono dentro de cada etapa (el cargador exige que toda
negación se decida en una etapa posterior) y los grados alcanzables forman un
conjunto finito, así que el ciclo termina siempre.

Con una base sin sección `inferencia_difusa`, o con anchos de transición nulos,
todos los grados valen 0 o 1 y el motor reproduce exactamente la inferencia
nítida de tres estados: la lógica clásica es un caso particular.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..dominio.campos import CAMPOS
from ..dominio.hechos import Accion, Estimacion, Instantanea, Motivo, Pendiente
from ..dominio.valores import Dato, Evidencia, Tri
from .base_conocimiento import NOMBRE_SOLICITUD, BaseConocimiento, ReglaProduccion
from .base_hechos import Activacion, BaseHechos, EvaluacionRama
from .calculos import Calculadora, CalculosTiempo
from .difuso import InferenciaDifusa, SalidaDifusa, borrosidad
from .lenguaje import Evaluador

VERSION_MOTOR = "1.0.0"

DECISIONES_VETO = frozenset({"CUARENTENA", "BLOQUEAR_INGRESO", "RETIRAR_LOTE", "CORREGIR_Y_REEVALUAR"})


@dataclass(frozen=True, slots=True)
class Resultado:
    decision_final: str
    rama_r30: str
    motivos: tuple[Motivo, ...]
    acciones_requeridas: tuple[Accion, ...]
    datos_pendientes: tuple[Pendiente, ...]
    estimaciones: tuple[Estimacion, ...]
    reglas_activadas: tuple[str, ...]
    calculos: CalculosTiempo
    fecha_proximo_control: datetime | None
    fecha_vencimiento_autorizacion: datetime | None
    solicitudes: dict[str, tuple[str, ...]]
    riesgo_activo: Tri
    version_base: str
    version_parametros: str
    version_motor: str
    hash_base: str
    traza: tuple[Activacion, ...]
    ramas: tuple[EvaluacionRama, ...]
    hechos_inferidos: tuple[str, ...]
    hechos_iniciales: tuple[tuple[str, object, str], ...]
    no_aplicables: tuple[str, ...]
    inferencia: InferenciaDifusa | None = None
    origen_decision: str = "NITIDO"
    grados_hechos: tuple[tuple[str, float], ...] = ()
    grados_solicitudes: tuple[tuple[str, float], ...] = ()


class Motor:
    def __init__(self, base: BaseConocimiento) -> None:
        self.base = base

    def evaluar(self, instantanea: Instantanea) -> Resultado:
        hechos = BaseHechos.desde(instantanea)
        evaluador = Evaluador(self.base, hechos, calculadora=None)
        calculadora = Calculadora(self.base, hechos, evaluador.definicion)
        evaluador.calculadora = calculadora
        calculadora.preparar()

        orden = 0
        for etapa in self.base.etapas:
            reglas = [r for r in self.base.reglas if r.etapa == etapa]
            limite = 4 * (len(reglas) + 2)
            for pasada in range(1, limite + 1):
                disparos = 0
                for regla in reglas:
                    previo = hechos.disparadas.get(regla.id)
                    if previo is not None and previo >= 1.0:
                        continue
                    alfa_aplica = 1.0
                    if regla.aplica_si is not None:
                        aplica = evaluador.grado(regla.aplica_si)
                        if aplica.cierto <= 0:
                            if previo is None and regla.regla not in hechos.no_aplicables:
                                hechos.no_aplicables.append(regla.regla)
                            continue
                        alfa_aplica = aplica.cierto
                    juicio = evaluador.evaluar(regla.si)
                    alfa = min(alfa_aplica, juicio.grado.cierto)
                    if alfa <= 0 or (previo is not None and alfa <= previo):
                        continue
                    orden += 1
                    self._disparar(
                        regla, alfa, juicio.grado.sup, juicio.soportes, hechos, evaluador,
                        etapa, pasada, orden, previo,
                    )
                    disparos += 1
                if disparos == 0:
                    break
            else:
                raise RuntimeError(f"la etapa {etapa} no alcanzó un punto fijo")

        hechos.pendientes = self._pendientes(hechos, evaluador, calculadora)
        self._degradar(hechos)

        decision, rama, grado_rama = self._resolver(hechos, evaluador)
        inferencia, decision, rama, origen = self._inferencia_difusa(
            hechos, evaluador, decision, rama, grado_rama
        )

        riesgo = evaluador.definicion("riesgo_activo") if "riesgo_activo" in self.base.definiciones else Tri.DESCONOCIDO
        monitoreo = hechos.pedida("MONITOREO") or decision == "AUTORIZAR_CON_MONITOREO"
        proximo = None if decision == "CUARENTENA" else calculadora.proximo_control(riesgo, monitoreo)
        vencimiento = (
            calculadora.vencimiento_autorizacion(proximo)
            if decision in self.base.decisiones_autorizadas
            else None
        )

        estimaciones: list[Estimacion] = []
        if calculadora.estimacion_hermetica is not None:
            estimaciones.append(calculadora.estimacion_hermetica)
        estimaciones.extend(calculadora.tiempo.estimaciones)

        return Resultado(
            decision_final=decision,
            rama_r30=rama,
            motivos=tuple(hechos.motivos),
            acciones_requeridas=tuple(hechos.acciones),
            datos_pendientes=tuple(hechos.pendientes),
            estimaciones=tuple(dict.fromkeys(estimaciones)),
            reglas_activadas=tuple(hechos.reglas_activadas),
            calculos=calculadora.tiempo,
            fecha_proximo_control=proximo,
            fecha_vencimiento_autorizacion=vencimiento,
            solicitudes={
                NOMBRE_SOLICITUD[s]: tuple(c) for s, c in hechos.solicitudes.items() if c
            },
            riesgo_activo=riesgo,
            version_base=self.base.version_base,
            version_parametros=self.base.version_parametros,
            version_motor=VERSION_MOTOR,
            hash_base=self.base.hash,
            traza=tuple(hechos.traza),
            ramas=tuple(hechos.ramas),
            hechos_inferidos=tuple(hechos.hallazgos),
            hechos_iniciales=tuple(hechos.iniciales()),
            no_aplicables=tuple(hechos.no_aplicables),
            inferencia=inferencia,
            origen_decision=origen,
            grados_hechos=tuple((h, hechos.grado_hecho(h)) for h in hechos.hallazgos),
            grados_solicitudes=tuple(
                (NOMBRE_SOLICITUD[s], g) for s, g in hechos.grados_solicitud.items() if g > 0
            ),
        )

    # --- Evaluación: Modus Ponens Generalizado ---------------------------------

    def _terminos_salida(self, regla: ReglaProduccion) -> tuple[str, ...]:
        modelo = self.base.modelo_difuso
        if modelo is None:
            return ()
        if regla.salida is not None:
            return (regla.salida,)
        return tuple(dict.fromkeys(
            modelo.consecuente_por_solicitud[s]
            for s in regla.entonces.solicitudes
            if s in modelo.consecuente_por_solicitud
        ))

    def _disparar(
        self,
        regla: ReglaProduccion,
        alfa: float,
        alfa_sup: float,
        soportes: tuple[str, ...],
        hechos: BaseHechos,
        evaluador: Evaluador,
        etapa: str,
        pasada: int,
        orden: int,
        previo: float | None,
    ) -> None:
        hechos.disparadas[regla.id] = alfa
        consecuente = regla.entonces
        hallazgo = consecuente.hallazgo

        if hallazgo:
            hechos.afirmar(hallazgo, alfa)
            if regla.registrar_motivo:
                motivo = Motivo(
                    id=f"{regla.regla}:{hallazgo}",
                    regla=regla.regla,
                    mensaje=self._redactar(consecuente.mensaje or "", soportes, hechos, evaluador, alfa),
                    evidencias=tuple(self._evidencia(e, hechos, evaluador) for e in regla.evidencias),
                    fuentes=self.base.fuentes_de(regla.regla),
                    fundamento=self.base.fundamento_de(regla.regla),
                    grado=alfa,
                )
                indice = next((i for i, m in enumerate(hechos.motivos) if m.id == motivo.id), None)
                if indice is None:
                    hechos.motivos.append(motivo)
                else:
                    hechos.motivos[indice] = motivo
                if regla.regla not in hechos.reglas_activadas:
                    hechos.reglas_activadas.append(regla.regla)
            if consecuente.accion:
                accion = Accion(
                    codigo=consecuente.accion["codigo"],
                    descripcion=self._redactar(consecuente.accion["descripcion"], soportes, hechos, evaluador, alfa),
                    responsable_requerido=consecuente.accion["responsable"],
                )
                if accion not in hechos.acciones:
                    hechos.acciones.append(accion)

        for solicitud in consecuente.solicitudes:
            hechos.solicitar(solicitud, regla.regla, alfa)

        hechos.traza.append(
            Activacion(
                orden=orden,
                etapa=etapa,
                pasada=pasada,
                produccion=regla.id,
                regla=regla.regla,
                hallazgo=hallazgo,
                soportes=soportes,
                solicitudes=tuple(NOMBRE_SOLICITUD[s] for s in consecuente.solicitudes),
                grado=alfa,
                grado_sup=max(alfa, alfa_sup),
                terminos_salida=self._terminos_salida(regla),
            )
        )

    def _evidencia(self, especificacion: Mapping[str, Any], hechos: BaseHechos, evaluador: Evaluador) -> Evidencia:
        dato = hechos.dato(especificacion["dato"])
        campo = "temperatura_grano" if dato.campo == "temperatura_grano_aplicable" else dato.campo
        if "es" in especificacion and self.base.modelo_difuso is not None:
            terminos = especificacion["es"]
            lista = [terminos] if isinstance(terminos, str) else list(terminos)
            grado, _ = evaluador.pertenencia(str(especificacion.get("variable", especificacion["dato"])), lista)
            return Evidencia(
                campo=campo,
                valor_observado=dato.valor,
                unidad=dato.unidad,
                fecha_observacion=dato.fecha_observacion,
                operador="PERTENENCIA",
                umbral=None,
                termino=" o ".join(lista),
                grado=None if grado.no_aplica or grado.desconocido else grado.cierto,
            )
        umbral: Any = None
        if "valor" in especificacion:
            umbral = evaluador.valor(especificacion["valor"])
            if isinstance(umbral, Dato):
                umbral = umbral.valor
        return Evidencia(
            campo=campo,
            valor_observado=dato.valor,
            unidad=dato.unidad,
            fecha_observacion=dato.fecha_observacion,
            operador=especificacion.get("op"),
            umbral=umbral,
        )

    _MARCADOR = re.compile(r"\{([^{}]+)\}")

    def _redactar(
        self, plantilla: str, soportes: tuple[str, ...], hechos: BaseHechos, evaluador: Evaluador,
        alfa: float = 1.0,
    ) -> str:
        """Rellena el mensaje de la regla con los valores de este caso."""

        def formato(valor: Any) -> str:
            if valor is None:
                return "desconocido"
            if isinstance(valor, Decimal):
                return format(valor.normalize(), "f") if valor == valor.to_integral() else str(valor)
            return str(valor)

        def sustituir(coincidencia: re.Match[str]) -> str:
            marcador = coincidencia.group(1)
            if marcador == "soportes":
                return ", ".join(dict.fromkeys(soportes)) or "sin detalle"
            if marcador == "invalidos":
                return ", ".join(hechos.invalidos())
            if marcador == "grado":
                return f"{alfa:.2f}"
            if "?" in marcador:
                condicion, opciones = marcador.split("?", 1)
                si, _, sino = opciones.partition("|")
                es_ingreso = hechos.instantanea.fase is not None and hechos.instantanea.fase.value == "INGRESO"
                return si if condicion == "ingreso" and es_ingreso else sino
            tipo, _, argumento = marcador.partition(":")
            if tipo == "dato":
                return formato(hechos.dato(argumento).valor)
            if tipo == "param":
                return formato(self.base.parametro(argumento))
            if tipo == "calculo":
                return formato(evaluador.calculadora.valor(argumento))
            if tipo == "fallidas":
                return "; ".join(evaluador.fallidas({"definicion": argumento})) or "sin detalle"
            if tipo in {"diferencia", "horas"}:
                a, b = (hechos.dato(c.strip()) for c in argumento.split(","))
                if tipo == "diferencia":
                    if a.numero is None or b.numero is None:
                        return "desconocido"
                    return formato(a.numero - b.numero)
                if a.fecha_observacion is None or b.fecha_observacion is None:
                    return "desconocido"
                horas = (a.fecha_observacion - b.fecha_observacion).total_seconds() / 3600
                return formato(Decimal(str(round(horas, 1))))
            return coincidencia.group(0)

        return self._MARCADOR.sub(sustituir, plantilla)

    # --- Datos exigibles ---------------------------------------------------------

    def _pendientes(self, hechos: BaseHechos, evaluador: Evaluador, calculadora: Calculadora) -> list[Pendiente]:
        salida: list[Pendiente] = []
        for exigible in self.base.datos_exigibles:
            if "cuando_desconocido" in exigible:
                activo = evaluador.grado(exigible["cuando_desconocido"]).desconocido
            else:
                activo = evaluador.grado(exigible["cuando"]).cierto >= 1.0
            if not activo:
                continue
            if "campos" in exigible:
                for campo in hechos.conjunto.desconocidos(exigible["campos"]):
                    paso = CAMPOS[campo].paso if campo in CAMPOS else 6
                    salida.append(Pendiente(campo, exigible["motivo"], paso))
            if "pendiente" in exigible:
                p = exigible["pendiente"]
                salida.append(Pendiente(p["campo"], p["motivo"], int(p.get("paso", 6))))
            if "pendientes_del_calculo" in exigible:
                campo = exigible["pendientes_del_calculo"]
                for motivo in calculadora.tiempo.motivos_no_disponible:
                    salida.append(Pendiente(campo, motivo, 5))
        unicos: dict[tuple[str, str], Pendiente] = {}
        for pendiente in salida:
            unicos.setdefault((pendiente.campo, pendiente.motivo), pendiente)
        return list(unicos.values())

    # --- Resolución jerárquica -----------------------------------------------------

    def _degradar(self, hechos: BaseHechos) -> None:
        """Una solicitud grave que no alcanza su corte-α se degrada con su grado.

        Un lote "60 % no apto" no justifica certeza para bloquear, pero sí es lo
        bastante adverso para corregir. Con grados 0 o 1 nunca se degrada nada.
        """
        modelo = self.base.modelo_difuso
        if modelo is None:
            return
        for origen, destino in modelo.degradacion.items():
            grado = hechos.grado_solicitud(origen)
            if 0 < grado < modelo.corte_degradacion:
                for causa in list(hechos.solicitudes.get(origen, ())):
                    hechos.solicitar(destino, causa, grado)

    def _resolver(self, hechos: BaseHechos, evaluador: Evaluador) -> tuple[str, str, float]:
        """Prioridad fija sobre cortes-α: gana la primera rama cuyo grado cierto alcanza su corte.

        Se evalúan todas las ramas para que la explicación pueda decir qué le
        faltó a cada autorización, aunque solo una emita la decisión.
        """
        elegida = None
        grado_elegida = 1.0
        for rama in self.base.resolucion:
            grado = evaluador.grado(rama.si)
            corte = self.base.corte_de(rama)
            aplica = grado.cierto > 0 and grado.cierto >= corte
            fallidas = () if aplica else tuple(evaluador.fallidas(rama.si))
            hechos.ramas.append(
                EvaluacionRama(
                    rama=rama.rama,
                    decision=rama.decision,
                    valor="VERDADERO" if aplica else grado.tri.value,
                    fallidas=fallidas,
                    grado=grado.cierto,
                    corte=corte,
                )
            )
            if elegida is None and aplica:
                elegida = rama
                grado_elegida = grado.cierto
        assert elegida is not None, "la última rama se aplica siempre"
        if elegida.mensaje:
            hechos.motivos.append(
                Motivo(
                    id=f"{elegida.rama}:SIN_CONCLUSION",
                    regla=elegida.rama,
                    mensaje=elegida.mensaje,
                    fuentes=self.base.fuentes_de(elegida.rama),
                    fundamento=self.base.fundamento_de(elegida.rama),
                )
            )
        return elegida.decision, elegida.rama, grado_elegida

    def _inferencia_difusa(
        self, hechos: BaseHechos, evaluador: Evaluador, decision: str, rama: str, grado_rama: float
    ) -> tuple[InferenciaDifusa | None, str, str, str]:
        """Agregación Mamdani, centroide y endurecimiento por índice de severidad."""
        modelo = self.base.modelo_difuso
        if modelo is None:
            return None, decision, rama, "NITIDO"

        if rama == "R30.5":
            origen = "PENDIENTES"
        elif grado_rama < 1.0:
            origen = "CORTE_ALFA"
        elif decision in DECISIONES_VETO:
            origen = "VETO"
        else:
            origen = "NITIDO"

        alturas: dict[str, float] = {}
        for activacion in hechos.traza:
            for termino in activacion.terminos_salida:
                alturas[termino] = max(alturas.get(termino, 0.0), activacion.grado)
        indice = modelo.salida.centroide(alturas)

        banda_nombre: str | None = None
        decision_indice: str | None = None
        if indice is not None:
            banda = modelo.banda(indice)
            banda_nombre = banda.decision
            decision_indice, rama_indice = banda.decision, banda.rama
            if banda.requiere is not None and evaluador.grado(banda.requiere).cierto < 1.0 and banda.si_no:
                decision_indice, rama_indice = banda.si_no
            if modelo.severidad.get(decision_indice, 0) > modelo.severidad.get(decision, 0):
                hechos.motivos.append(
                    Motivo(
                        id=f"{rama_indice}:INDICE_SEVERIDAD",
                        regla=rama_indice,
                        mensaje=(
                            f"El índice de severidad difuso (centroide del conjunto agregado) es "
                            f"{indice:.1f} sobre 100 y corresponde a {banda.decision}: la decisión "
                            f"se endurece de {decision} a {decision_indice} aunque ninguna solicitud "
                            f"alcance por sí sola su corte-α."
                        ),
                        fuentes=self.base.fuentes_de(rama_indice),
                        fundamento=self.base.fundamento_de(rama_indice),
                        grado=1.0,
                    )
                )
                decision, rama, origen = decision_indice, rama_indice, "INDICE"

        pertenencias = tuple(hechos.pertenencias[k] for k in sorted(hechos.pertenencias))
        salida = SalidaDifusa(
            variable=modelo.salida.nombre,
            alturas=tuple(sorted(alturas.items())),
            metodo="CENTROIDE",
            indice=indice,
            banda=banda_nombre,
            decision_indice=decision_indice,
        )
        inferencia = InferenciaDifusa(
            pertenencias=pertenencias,
            salida=salida,
            origen_decision=origen,
            borrosidad=borrosidad([p.grado for p in pertenencias]),
        )
        return inferencia, decision, rama, origen


__all__ = ["Motor", "Resultado", "VERSION_MOTOR"]
