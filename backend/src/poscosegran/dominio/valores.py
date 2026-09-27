"""Lógica de tres estados y acceso a los datos de una evaluación.

Sección 2.2 de la base: VERDADERO, FALSO y DESCONOCIDO. NO_APLICA solo donde la
especificación lo excluye expresamente. Un dato ausente nunca se convierte en
condición favorable, y un dato inválido no participa en comparaciones numéricas.
"""

from __future__ import annotations

import enum
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


class Tri(enum.Enum):
    VERDADERO = "VERDADERO"
    FALSO = "FALSO"
    DESCONOCIDO = "DESCONOCIDO"
    NO_APLICA = "NO_APLICA"

    def __bool__(self) -> bool:  
        raise TypeError("use Tri.VERDADERO explícitamente; el valor de verdad no es binario")

    @property
    def cierto(self) -> bool:
        return self is Tri.VERDADERO


V = Tri.VERDADERO
F = Tri.FALSO
D = Tri.DESCONOCIDO
NA = Tri.NO_APLICA


def y(*valores: Tri) -> Tri:
    """Conjunción: un FALSO basta; si no hay falsos y falta información, DESCONOCIDO."""
    efectivos = [valor for valor in valores if valor is not NA]
    if not efectivos:
        return NA
    if any(valor is F for valor in efectivos):
        return F
    if any(valor is D for valor in efectivos):
        return D
    return V


def o(*valores: Tri) -> Tri:
    """Disyunción: un VERDADERO basta; si no hay verdaderos y falta información, DESCONOCIDO."""
    efectivos = [valor for valor in valores if valor is not NA]
    if not efectivos:
        return NA
    if any(valor is V for valor in efectivos):
        return V
    if any(valor is D for valor in efectivos):
        return D
    return F


def no(valor: Tri) -> Tri:
    """Negar DESCONOCIDO produce DESCONOCIDO."""
    if valor is V:
        return F
    if valor is F:
        return V
    return valor


# ---------------------------------------------------------------------------
# Grado de verdad difuso con incertidumbre (extensión conservadora de Kleene)
# ---------------------------------------------------------------------------
#
# La teoría de conjuntos difusos del sistema es (F(U), mín, máx, 1 - x): la
# t-norma y la t-conorma de Zadeh con la negación estándar, que es fuerte e
# involutiva y dual de ambas por De Morgan.
#
# Un grado es un intervalo [inf, sup] contenido en [0, 1]. Un dato difuso
# conocido tiene inf = sup = μ; un dato desconocido es [0, 1], y la ausencia de
# información se propaga en lugar de convertirse en una condición favorable.
# Sobre {[0,0], [1,1], [0,1]} las operaciones coinciden exactamente con la
# lógica de tres estados y(), o() y no(): la lógica actual es un caso particular.

PRECISION_GRADO = 6


def _redondear(valor: float) -> float:
    return round(min(1.0, max(0.0, float(valor))), PRECISION_GRADO)


@dataclass(frozen=True, slots=True)
class Grado:
    """Grado de verdad difuso: [inf, sup] ⊆ [0, 1], o NO_APLICA."""

    inf: float
    sup: float
    no_aplica: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "inf", _redondear(self.inf))
        object.__setattr__(self, "sup", _redondear(self.sup))
        if self.inf > self.sup:
            raise ValueError(f"grado mal formado: [{self.inf}, {self.sup}]")

    @classmethod
    def exacto(cls, valor: float) -> "Grado":
        return cls(valor, valor)

    @classmethod
    def desde_tri(cls, valor: Tri) -> "Grado":
        if valor is Tri.VERDADERO:
            return G_V
        if valor is Tri.FALSO:
            return G_F
        if valor is Tri.NO_APLICA:
            return G_NA
        return G_D

    @property
    def cierto(self) -> float:
        """Grado que se puede afirmar con la información disponible (α⁻)."""
        return 0.0 if self.no_aplica else self.inf

    @property
    def desconocido(self) -> bool:
        """Falta información: el grado real puede estar en cualquier punto de [inf, sup]."""
        return not self.no_aplica and self.inf < self.sup

    @property
    def tri(self) -> Tri:
        """Proyección a tres estados para los consumidores nítidos.

        Un grado parcial conocido se proyecta como DESCONOCIDO: ni se afirma ni se
        niega, que es la lectura conservadora para quien solo entiende V/F/D.
        """
        if self.no_aplica:
            return Tri.NO_APLICA
        if self.inf >= 1.0:
            return Tri.VERDADERO
        if self.sup <= 0.0:
            return Tri.FALSO
        return Tri.DESCONOCIDO


G_V = Grado(1.0, 1.0)
G_F = Grado(0.0, 0.0)
G_D = Grado(0.0, 1.0)
G_NA = Grado(0.0, 0.0, no_aplica=True)


def conjuncion(*grados: Grado) -> Grado:
    """t-norma mínimo de Zadeh sobre ambas cotas; NO_APLICA no participa."""
    efectivos = [g for g in grados if not g.no_aplica]
    if not efectivos:
        return G_NA
    return Grado(min(g.inf for g in efectivos), min(g.sup for g in efectivos))


def disyuncion(*grados: Grado) -> Grado:
    """t-conorma máximo de Zadeh sobre ambas cotas; NO_APLICA no participa."""
    efectivos = [g for g in grados if not g.no_aplica]
    if not efectivos:
        return G_NA
    return Grado(max(g.inf for g in efectivos), max(g.sup for g in efectivos))


def negacion(grado: Grado) -> Grado:
    """Negación estándar n(x) = 1 - x extendida a intervalos: [1 - sup, 1 - inf]."""
    if grado.no_aplica:
        return G_NA
    return Grado(1.0 - grado.sup, 1.0 - grado.inf)


class EstadoDato(enum.Enum):
    VALIDO = "VALIDO"
    DESCONOCIDO = "DESCONOCIDO"
    INVALIDO = "INVALIDO"
    VENCIDO = "VENCIDO"


class Procedencia(enum.Enum):
    ACTUAL = "ACTUAL"
    HISTORICA = "HISTORICA"
    ESTIMADA = "ESTIMADA"


@dataclass(frozen=True, slots=True)
class Dato:
    """Una observación ya validada, tal como la usa el motor."""

    campo: str
    estado: EstadoDato = EstadoDato.DESCONOCIDO
    valor: Decimal | bool | str | datetime | None = None
    unidad: str | None = None
    fecha_observacion: datetime | None = None
    metodo: str | None = None
    procedencia: Procedencia = Procedencia.ACTUAL
    no_aplica: bool = False
    motivo_no_aplica: str | None = None

    @property
    def utilizable(self) -> bool:
        """Solo un dato VALIDO participa en comparaciones."""
        return self.estado is EstadoDato.VALIDO and self.valor is not None and not self.no_aplica

    @property
    def numero(self) -> Decimal | None:
        if not self.utilizable:
            return None
        if isinstance(self.valor, bool):
            return None
        if isinstance(self.valor, Decimal):
            return self.valor
        try:
            return Decimal(str(self.valor))
        except (ArithmeticError, ValueError):
            return None

    @property
    def booleano(self) -> Tri:
        if self.no_aplica:
            return NA
        if not self.utilizable or not isinstance(self.valor, bool):
            return D
        return V if self.valor else F

    @property
    def fecha(self) -> datetime | None:
        """Para campos de tipo fecha: el valor, no la fecha de observación."""
        return self.valor if self.utilizable and isinstance(self.valor, datetime) else None

    @property
    def texto(self) -> str | None:
        return self.valor if self.utilizable and isinstance(self.valor, str) else None


AUSENTE = Dato(campo="", estado=EstadoDato.DESCONOCIDO)


@dataclass(frozen=True, slots=True)
class Evidencia:
    """Par valor observado / umbral con el operador que los comparó."""

    campo: str
    valor_observado: Decimal | bool | str | datetime | None = None
    unidad: str | None = None
    fecha_observacion: datetime | None = None
    operador: str | None = None
    umbral: Decimal | bool | str | datetime | None = None
    termino: str | None = None
    grado: float | None = None


def evidencia(dato: Dato, operador: str | None = None, umbral: object = None) -> Evidencia:
    return Evidencia(
        campo=dato.campo,
        valor_observado=dato.valor,
        unidad=dato.unidad,
        fecha_observacion=dato.fecha_observacion,
        operador=operador,
        umbral=umbral,  
    )


def mayor(dato: Dato, umbral: Decimal) -> Tri:
    numero = dato.numero
    if numero is None:
        return NA if dato.no_aplica else D
    return V if numero > umbral else F


def mayor_igual(dato: Dato, umbral: Decimal) -> Tri:
    numero = dato.numero
    if numero is None:
        return NA if dato.no_aplica else D
    return V if numero >= umbral else F


def menor(dato: Dato, umbral: Decimal) -> Tri:
    numero = dato.numero
    if numero is None:
        return NA if dato.no_aplica else D
    return V if numero < umbral else F


def menor_igual(dato: Dato, umbral: Decimal) -> Tri:
    numero = dato.numero
    if numero is None:
        return NA if dato.no_aplica else D
    return V if numero <= umbral else F


def entre(dato: Dato, minimo: Decimal, maximo: Decimal) -> Tri:
    return y(mayor_igual(dato, minimo), menor_igual(dato, maximo))


def comparar(izquierda: Dato, operador: str, derecha: Dato) -> Tri:
    """Compara dos datos observados. Si falta cualquiera, DESCONOCIDO."""
    a, b = izquierda.numero, derecha.numero
    if a is None or b is None:
        return D
    match operador:
        case "GT":
            return V if a > b else F
        case "GTE":
            return V if a >= b else F
        case "LT":
            return V if a < b else F
        case "LTE":
            return V if a <= b else F
        case _:  
            raise ValueError(f"operador no admitido: {operador}")


@dataclass(frozen=True, slots=True)
class Conjunto:
    """Datos de la evaluación, indexados por campo canónico."""

    datos: Mapping[str, Dato] = field(default_factory=dict)

    def __getitem__(self, campo: str) -> Dato:
        dato = self.datos.get(campo)
        return dato if dato is not None else Dato(campo=campo)

    def booleano(self, campo: str) -> Tri:
        return self[campo].booleano

    def presentes(self, campos: Iterable[str]) -> Tri:
        """VERDADERO si todos los campos tienen dato utilizable."""
        faltan = [campo for campo in campos if not self[campo].utilizable]
        return V if not faltan else D

    def desconocidos(self, campos: Iterable[str]) -> list[str]:
        return [campo for campo in campos if not self[campo].utilizable and not self[campo].no_aplica]

    def invalidos(self) -> list[str]:
        return sorted(
            campo
            for campo, dato in self.datos.items()
            if dato.estado in (EstadoDato.INVALIDO, EstadoDato.VENCIDO)
        )
