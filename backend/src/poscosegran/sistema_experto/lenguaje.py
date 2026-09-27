"""Evaluador del lenguaje de condiciones.

Interpreta los nodos de la base de conocimiento con grados de verdad difusos. No
hay eval ni exec: cada operador tiene una implementación explícita y cerrada, y un
operador que no está en la lista de base_conocimiento.OPERADORES no se admite.

Cada evaluación devuelve un `Grado` [inf, sup] ⊆ [0, 1] (valores.py):

    todos      t-norma mínimo de Zadeh (producto cartesiano de antecedentes)
    alguno     t-conorma máximo
    negar      negación estándar 1 - x
    difuso     pertenencia de una lectura a un término lingüístico (fuzzificación
               singleton)

Los átomos nítidos (booleanos observados, contexto, fechas, comparaciones con
límites normativos) producen grados 0 o 1, y la ausencia de información produce
[0, 1]. Sobre esos valores las operaciones coinciden exactamente con la lógica de
tres estados anterior, que queda como caso particular.

Además del grado, cada evaluación devuelve sus soportes: las condiciones concretas
que la hicieron (parcialmente) verdadera. El módulo de explicación los usa para
responder "¿por qué?".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..dominio.valores import (
    D,
    Dato,
    F,
    G_D,
    G_F,
    G_NA,
    G_V,
    NA,
    Grado,
    Tri,
    V,
    conjuncion,
    disyuncion,
    negacion,
)
from .base_conocimiento import NOMBRE_SOLICITUD, BaseConocimiento
from .base_hechos import BaseHechos
from .difuso import Pertenencia, VariableLinguistica


@dataclass(frozen=True, slots=True)
class Juicio:
    grado: Grado
    soportes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "soportes", tuple(dict.fromkeys(self.soportes)))

    @property
    def valor(self) -> Tri:
        """Proyección a tres estados, para los consumidores nítidos."""
        return self.grado.tri


def _j(valor: Tri, soportes: tuple[str, ...] = ()) -> Juicio:
    return Juicio(Grado.desde_tri(valor), soportes)


def sumar_mes_calendario(fecha: datetime) -> datetime:
    """Conserva el día; si no existe en el mes siguiente, usa el último día."""
    anio, mes = (fecha.year + 1, 1) if fecha.month == 12 else (fecha.year, fecha.month + 1)
    for dia in range(fecha.day, 0, -1):
        try:
            return fecha.replace(year=anio, month=mes, day=dia)
        except ValueError:
            continue
    raise ValueError("fecha no representable")


def _comparar(izquierda: Decimal, operador: str, derecha: Decimal) -> Tri:
    resultado = {
        "GT": izquierda > derecha,
        "GTE": izquierda >= derecha,
        "LT": izquierda < derecha,
        "LTE": izquierda <= derecha,
        "EQ": izquierda == derecha,
        "NEQ": izquierda != derecha,
    }[operador]
    return V if resultado else F


def _como_decimal(valor: Any) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (ArithmeticError, ValueError):
        return None


class Evaluador:
    def __init__(self, base: BaseConocimiento, hechos: BaseHechos, calculadora: Any) -> None:
        self.base = base
        self.hechos = hechos
        self.calculadora = calculadora
        self._evaluando: set[str] = set()

    def valor(self, nodo: Any) -> Any:
        """Resuelve un valor: literal, parámetro, dato observado o elección."""
        if isinstance(nodo, Mapping):
            if "param" in nodo:
                return self.base.parametro(nodo["param"])
            if "dato" in nodo:
                return self.hechos.dato(nodo["dato"])
            if "elegir" in nodo:
                eleccion = nodo["elegir"]
                rama = "entonces" if self.evaluar(eleccion["si"]).grado.cierto >= 1.0 else "sino"
                return self.valor(eleccion[rama])
        if isinstance(nodo, bool) or isinstance(nodo, str):
            return nodo
        return _como_decimal(nodo)

    def evaluar(self, nodo: Mapping[str, Any]) -> Juicio:
        operador = next(
            k for k in nodo
            if k != "descripcion" and k not in {"op", "valor", "en", "igual", "definido", "dias", "meses", "es"}
        )
        metodo = getattr(self, f"_op_{operador}")
        juicio: Juicio = metodo(nodo)
        return juicio

    def grado(self, nodo: Mapping[str, Any]) -> Grado:
        return self.evaluar(nodo).grado

    def definicion(self, nombre: str) -> Tri:
        """Proyección a tres estados de una definición (consumidores nítidos)."""
        return self._op_definicion({"definicion": nombre}).valor

    def grado_definicion(self, nombre: str) -> Grado:
        return self._op_definicion({"definicion": nombre}).grado

    def descripcion(self, nodo: Mapping[str, Any]) -> str | None:
        texto = nodo.get("descripcion")
        return str(texto) if texto else None

    def _soportes(self, nodo: Mapping[str, Any], juicio: Juicio) -> tuple[str, ...]:
        """Un nodo descrito se resume en su descripción; si no, en sus propios soportes."""
        descripcion = self.descripcion(nodo)
        return (descripcion,) if descripcion else juicio.soportes

    # --- Conectivas ---------------------------------------------------------

    def _op_todos(self, nodo: Mapping[str, Any]) -> Juicio:
        juicios = [(hijo, self.evaluar(hijo)) for hijo in nodo["todos"]]
        grado = conjuncion(*(j.grado for _, j in juicios))
        soportes: tuple[str, ...] = ()
        if grado.cierto > 0:
            for hijo, juicio in juicios:
                if juicio.grado.cierto > 0:
                    soportes += self._soportes(hijo, juicio)
        return Juicio(grado, soportes)

    def _op_alguno(self, nodo: Mapping[str, Any]) -> Juicio:
        juicios = [(hijo, self.evaluar(hijo)) for hijo in nodo["alguno"]]
        grado = disyuncion(*(j.grado for _, j in juicios))
        soportes: tuple[str, ...] = ()
        if grado.cierto > 0:
            for hijo, juicio in juicios:
                if juicio.grado.cierto > 0:
                    soportes += self._soportes(hijo, juicio)
        return Juicio(grado, soportes)

    def _op_negar(self, nodo: Mapping[str, Any]) -> Juicio:
        """Negar DESCONOCIDO produce DESCONOCIDO: la negación no crea información."""
        return Juicio(negacion(self.evaluar(nodo["negar"]).grado))

    def _op_implica(self, nodo: Mapping[str, Any]) -> Juicio:
        """Si el antecedente no se cumple en absoluto, la condición no aplica.

        Con antecedente pleno se evalúa el consecuente; con antecedente parcial α se
        usa la implicación material ¬A ∨ B = máx(1 - α, B).
        """
        partes = nodo["implica"]
        antecedente = self.evaluar(partes["si"]).grado
        if antecedente.no_aplica or antecedente.cierto <= 0:
            return Juicio(G_NA)
        consecuente = self.evaluar(partes["entonces"])
        if antecedente.cierto >= 1.0:
            return consecuente
        grado = disyuncion(Grado.exacto(1.0 - antecedente.cierto), consecuente.grado)
        return Juicio(grado, consecuente.soportes)

    def _op_guarda(self, nodo: Mapping[str, Any]) -> Juicio:
        """Sin el dato de guarda la condición completa es DESCONOCIDO, no FALSO."""
        partes = nodo["guarda"]
        dato = self.hechos.dato(partes["campo"])
        if dato.no_aplica:
            return Juicio(G_NA)
        if not dato.utilizable:
            return Juicio(G_D)
        return self.evaluar(partes["entonces"])

    def _op_es_verdadero(self, nodo: Mapping[str, Any]) -> Juicio:
        """Grado cierto: [inf, inf]. NO_APLICA y lo desconocido no se afirman."""
        juicio = self.evaluar(nodo["es_verdadero"])
        if juicio.grado.no_aplica:
            return Juicio(G_F)
        return Juicio(Grado.exacto(juicio.grado.inf), juicio.soportes if juicio.grado.inf > 0 else ())

    def _op_es_falso(self, nodo: Mapping[str, Any]) -> Juicio:
        """Grado en que la condición es con certeza falsa: 1 - sup."""
        grado = self.evaluar(nodo["es_falso"]).grado
        if grado.no_aplica:
            return Juicio(G_F)
        return Juicio(Grado.exacto(1.0 - grado.sup))

    def _op_es_desconocido(self, nodo: Mapping[str, Any]) -> Juicio:
        """Amplitud de la incertidumbre: sup - inf (1 si nada se sabe)."""
        grado = self.evaluar(nodo["es_desconocido"]).grado
        if grado.no_aplica:
            return Juicio(G_F)
        return Juicio(Grado.exacto(grado.sup - grado.inf))

    def _op_no_falso(self, nodo: Mapping[str, Any]) -> Juicio:
        """Grado posible: sup (verdadero o desconocido)."""
        grado = self.evaluar(nodo["no_falso"]).grado
        if grado.no_aplica:
            return Juicio(G_F)
        return Juicio(Grado.exacto(grado.sup))

    def _op_constante(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j({"VERDADERO": V, "FALSO": F, "DESCONOCIDO": D}[nodo["constante"]])

    def _op_siempre(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(G_V)

    # --- Átomos nítidos -------------------------------------------------------

    def _op_dato(self, nodo: Mapping[str, Any]) -> Juicio:
        valor, soporte = self._dato_nitido(nodo)
        return _j(valor, soporte if valor is V else ())

    def _dato_nitido(self, nodo: Mapping[str, Any]) -> tuple[Tri, tuple[str, ...]]:
        campo = nodo["dato"]
        dato = self.hechos.dato(campo)
        soporte = (campo,)

        if "en" in nodo:
            if dato.no_aplica:
                return NA, ()
            texto = dato.texto
            if texto is None:
                return D, ()
            return (V if texto in nodo["en"] else F), soporte

        if "op" not in nodo:
            return dato.booleano, soporte

        operador = nodo["op"]
        derecha = self.valor(nodo["valor"])

        if isinstance(derecha, Dato):
            if operador in {"EQ", "NEQ"} and (dato.texto is not None or derecha.texto is not None):
                if dato.texto is None or derecha.texto is None:
                    return D, ()
                igual = dato.texto == derecha.texto
                return (V if igual == (operador == "EQ") else F), soporte
            a, b = dato.numero, derecha.numero
            if a is None or b is None:
                return D, ()
            return _comparar(a, operador, b), soporte

        if isinstance(derecha, bool):
            valor = dato.booleano
            if valor in (NA, D):
                return valor, ()
            coincide = (valor is V) == derecha
            return (V if coincide == (operador == "EQ") else F), soporte

        if isinstance(derecha, str):
            if dato.no_aplica:
                return NA, ()
            texto = dato.texto
            if texto is None:
                return D, ()
            igual = texto == derecha
            return (V if igual == (operador == "EQ") else F), soporte

        numero = dato.numero
        if numero is None:
            return (NA if dato.no_aplica else D), ()
        if derecha is None:
            return D, ()
        return _comparar(numero, operador, derecha), soporte

    def _op_aportado(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j(V if self.hechos.dato(nodo["aportado"]).utilizable else F)

    def _op_presentes(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j(V if all(self.hechos.dato(c).utilizable for c in nodo["presentes"]) else D)

    def _op_conocidos(self, nodo: Mapping[str, Any]) -> Juicio:
        faltan = [
            c for c in nodo["conocidos"]
            if not self.hechos.dato(c).utilizable and not self.hechos.dato(c).no_aplica
        ]
        return _j(V if not faltan else D)

    def _op_vigente_meses(self, nodo: Mapping[str, Any]) -> Juicio:
        dato = self.hechos.dato(nodo["vigente_meses"])
        if dato.no_aplica:
            return Juicio(G_NA)
        referencia = dato.fecha
        if referencia is None:
            return Juicio(G_D)
        limite = referencia
        for _ in range(int(nodo.get("meses", 1))):
            limite = sumar_mes_calendario(limite)
        return _j(V if self.hechos.instantanea.fecha_evaluacion <= limite else F)

    def _op_vencido_dias(self, nodo: Mapping[str, Any]) -> Juicio:
        """Un registro inexistente no es un atraso con fecha inventada: DESCONOCIDO."""
        referencia = self.hechos.dato(nodo["vencido_dias"]).fecha
        if referencia is None:
            return Juicio(G_D)
        dias = self.valor(nodo["dias"])
        vence = referencia + timedelta(days=float(dias))
        return _j(V if self.hechos.instantanea.fecha_evaluacion > vence else F)

    def _op_horas_entre(self, nodo: Mapping[str, Any]) -> Juicio:
        a, b = (self.hechos.dato(c) for c in nodo["horas_entre"])
        if a.fecha_observacion is None or b.fecha_observacion is None:
            return Juicio(G_D)
        horas = Decimal(str((a.fecha_observacion - b.fecha_observacion).total_seconds() / 3600))
        derecha = self.valor(nodo["valor"])
        return _j(_comparar(horas, nodo["op"], derecha))

    def _op_diferencia(self, nodo: Mapping[str, Any]) -> Juicio:
        a, b = (self.hechos.dato(c).numero for c in nodo["diferencia"])
        if a is None or b is None:
            return Juicio(G_D)
        return _j(_comparar(a - b, nodo["op"], self.valor(nodo["valor"])))

    # --- Hechos inferidos, solicitudes y contexto -----------------------------

    def _op_hecho(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["hecho"]
        grado = self.hechos.grado_hecho(nombre)
        return Juicio(Grado.exacto(grado), (nombre,) if grado > 0 else ())

    def _op_algun_hecho(self, nodo: Mapping[str, Any]) -> Juicio:
        grados = {n: self.hechos.grado_hecho(n) for n in nodo["algun_hecho"]}
        presentes = tuple(n for n, g in grados.items() if g > 0)
        return Juicio(Grado.exacto(max(grados.values(), default=0.0)), presentes)

    def _op_solicitud(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["solicitud"]
        grado = self.hechos.grado_solicitud(nombre)
        return Juicio(Grado.exacto(grado), (NOMBRE_SOLICITUD[nombre],) if grado > 0 else ())

    def _op_episodio(self, nodo: Mapping[str, Any]) -> Juicio:
        abiertos = self.hechos.episodios_abiertos(list(nodo["episodio"]))
        if not abiertos:
            return Juicio(G_F)
        return Juicio(G_V, tuple(f"EPISODIO_{e.tipo}_ABIERTO" for e in abiertos))

    def _op_contexto(self, nodo: Mapping[str, Any]) -> Juicio:
        """Fase y modalidad son hechos del contexto: su igualdad es binaria."""
        inst = self.hechos.instantanea
        nombre = nodo["contexto"]
        if nombre == "clima_calido":
            return _j(inst.clima_calido)
        actual = inst.fase if nombre == "fase" else inst.tipo_almacenamiento
        if nodo.get("definido"):
            return _j(V if actual is not None else F)
        valor = actual.value if actual is not None else None
        return _j(V if valor == nodo.get("igual") else F)

    def _op_definicion(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["definicion"]
        if nombre in self._evaluando:
            raise RuntimeError(f"ciclo al evaluar la definición {nombre}")
        self._evaluando.add(nombre)
        try:
            definicion = self.base.definiciones[nombre]
            juicio = self.evaluar(definicion)
        finally:
            self._evaluando.discard(nombre)
        if juicio.grado.cierto > 0:
            return Juicio(juicio.grado, (definicion.get("descripcion") or nombre,))
        return Juicio(juicio.grado)

    def _op_calculo(self, nodo: Mapping[str, Any]) -> Juicio:
        valor = self.calculadora.valor(nodo["calculo"])
        if "op" not in nodo:
            if isinstance(valor, Tri):
                return _j(valor)
            if isinstance(valor, bool):
                return _j(V if valor else F)
            return _j(D if valor is None else V)
        izquierda = _como_decimal(valor)
        derecha = self.valor(nodo["valor"])
        if izquierda is None or derecha is None:
            return Juicio(G_D)
        return _j(_comparar(izquierda, nodo["op"], derecha))

    def _op_nulo(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j(V if self.calculadora.valor(nodo["nulo"]) is None else F)

    def _op_hay_invalidos(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j(V if self.hechos.invalidos() else F)

    def _op_inconsistencia(self, nodo: Mapping[str, Any]) -> Juicio:
        """Contradicciones detectadas fuera del motor, al consolidar el historial."""
        nombre = nodo["inconsistencia"]
        registradas = self.hechos.instantanea.datos_inconsistentes
        coincidentes = tuple(registradas) if nombre == "*" else tuple(r for r in registradas if r == nombre)
        return Juicio(G_V, coincidentes) if coincidentes else Juicio(G_F)

    def _op_pendientes(self, nodo: Mapping[str, Any]) -> Juicio:
        return _j(V if self.hechos.pendientes else F)

    # --- Fuzzificación --------------------------------------------------------

    def lectura(self, variable: VariableLinguistica) -> tuple[Decimal | None, bool]:
        """Valor nítido de la variable (singleton) y si no aplica."""
        if variable.fuente == "dato":
            dato = self.hechos.dato(variable.argumentos[0])
            return dato.numero, dato.no_aplica
        if variable.fuente == "diferencia":
            a, b = (self.hechos.dato(c).numero for c in variable.argumentos)
            return (a - b if a is not None and b is not None else None), False
        valor = _como_decimal(self.calculadora.valor(variable.argumentos[0]))
        return valor, False

    def pertenencia(self, nombre_variable: str, terminos: list[str]) -> tuple[Grado, float | None]:
        """Grado en que la lectura pertenece al término o a la etiqueta compuesta."""
        modelo = self.base.modelo_difuso
        assert modelo is not None, "la base no declara inferencia_difusa"
        variable = modelo.variables[nombre_variable]
        numero, no_aplica = self.lectura(variable)
        if numero is None:
            return (G_NA if no_aplica else G_D), None
        x = float(numero)
        grados = variable.fuzzificar(x)
        for termino, grado in grados.items():
            self.hechos.pertenencias[(nombre_variable, termino)] = Pertenencia(
                variable=nombre_variable, termino=termino, valor=x, unidad=variable.unidad, grado=grado
            )
        return Grado.exacto(variable.grado_union(terminos, x)), x

    def _op_difuso(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["difuso"]
        terminos = nodo["es"]
        lista = [terminos] if isinstance(terminos, str) else list(terminos)
        grado, _ = self.pertenencia(nombre, lista)
        if grado.cierto <= 0:
            return Juicio(grado)
        return Juicio(grado, (f"{nombre} {' o '.join(lista)} (μ = {grado.cierto:.2f})",))

    # --- Explicación: ¿por qué no? --------------------------------------------

    def _estado(self, nodo: Mapping[str, Any], grado: Grado) -> str:
        """Los envoltorios aplanan NO_APLICA y lo desconocido a un grado; aquí se recupera."""
        for envoltura in ("es_verdadero", "no_falso"):
            if envoltura in nodo:
                grado = self.evaluar(nodo[envoltura]).grado
        if grado.no_aplica:
            return "no aplica"
        if grado.desconocido:
            return "desconocido"
        if grado.cierto <= 0:
            return "no se cumple"
        return f"se cumple solo en grado {grado.cierto:.2f}"

    @staticmethod
    def _sin_descripcion(nodo: Mapping[str, Any]) -> Mapping[str, Any]:
        return {k: v for k, v in nodo.items() if k != "descripcion"}

    def fallidas(self, nodo: Mapping[str, Any]) -> list[str]:
        """Descripciones de las partes que impidieron que la condición se cumpliera del todo.

        Es la base del "¿por qué no?": recorre conjunciones, implicaciones y
        definiciones hasta encontrar las condiciones descritas que fallaron.
        """
        if self.evaluar(nodo).grado.cierto >= 1.0:
            return []
        if "todos" in nodo:
            salida: list[str] = []
            for hijo in nodo["todos"]:
                grado = self.evaluar(hijo).grado
                if grado.no_aplica or grado.cierto >= 1.0:
                    continue
                descripcion = self.descripcion(hijo)
                if descripcion:
                    estado = self._estado(hijo, grado)
                    detalle = [d for d in self.fallidas(self._sin_descripcion(hijo)) if d != descripcion]
                    texto = f"{descripcion} ({estado})"
                    if detalle and estado != "no aplica":
                        texto += ": " + "; ".join(detalle)
                    salida.append(texto)
                else:
                    salida.extend(self.fallidas(hijo))
            return salida
        if "implica" in nodo:
            return self.fallidas(nodo["implica"]["entonces"])
        if "guarda" in nodo:
            campo = nodo["guarda"]["campo"]
            if not self.hechos.dato(campo).utilizable:
                return [f"falta {campo}"]
            return self.fallidas(nodo["guarda"]["entonces"])
        if "definicion" in nodo:
            return self.fallidas(self._sin_descripcion(self.base.definiciones[nodo["definicion"]]))
        for envoltura in ("es_verdadero", "no_falso"):
            if envoltura in nodo:
                return self.fallidas(nodo[envoltura])
        descripcion = self.descripcion(nodo)
        return [descripcion] if descripcion else []
