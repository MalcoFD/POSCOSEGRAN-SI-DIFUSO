"""Componentes difusos del sistema experto: fuzzificación, agregación y defuzzificación.

La teoría de conjuntos difusos adoptada es (F(U), mín, máx, 1 - x), con
implicación de Mamdani, composición sup-min, agregación por máximo y
defuzzificación por centroide. Este módulo no contiene conocimiento del dominio:
todas las variables, términos, cortes y bandas se leen de la base de conocimiento
(sección `inferencia_difusa` de base_conocimiento.yaml).

Funciones de pertenencia admitidas (nomenclatura del material del curso):

    triangular [a, m, b]          a < m < b
    trapezoidal [a, b, c, d]      a <= b <= c <= d
    gamma_lineal [a, m]           0 hasta a, rampa, 1 desde m (extremo abierto superior)
    l_lineal [a, m]               1 hasta a, rampa, 0 desde m (extremo abierto inferior)
    s [a, m, b] / z [a, m, b]     polinómicas de soporte acotado, m = (a + b) / 2
    gaussiana {m, k}              e^(-k (x - m)^2), k > 0
    singleton a                   1 solo en a

Una variable también puede definirse por `cortes`: los umbrales publicados de la
base son las anclas y cada corte coloca una rampa de ancho δ del lado seguro. Con
δ = 0 los términos degeneran en conjuntos nítidos que respetan el operador
original (≤ o <), de modo que la lógica nítida queda como caso particular.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

INFERIOR = "INFERIOR"
SUPERIOR = "SUPERIOR"

TEORIA_ADMITIDA: Mapping[str, frozenset[str]] = {
    "t_norma": frozenset({"MINIMO"}),
    "t_conorma": frozenset({"MAXIMO"}),
    "negacion": frozenset({"ESTANDAR"}),
    "implicacion": frozenset({"MAMDANI"}),
    "composicion": frozenset({"SUP_MIN"}),
    "agregacion": frozenset({"MAXIMO"}),
    "defuzzificacion": frozenset({"CENTROIDE"}),
}

FUENTES = frozenset({"dato", "diferencia", "calculo"})


def _r(valor: float) -> float:
    return round(min(1.0, max(0.0, valor)), 6)


class FuncionPertenencia(Protocol):
    def grado(self, x: float) -> float: ...

    def describir(self) -> str: ...


# ---------------------------------------------------------------------------
# Funciones de pertenencia
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Trapezoidal:
    """μ(x) por tramos con núcleo [b, c]. Admite ±∞ para los extremos abiertos."""

    a: float
    b: float
    c: float
    d: float
    nombre_forma: str = "trapezoidal"

    def grado(self, x: float) -> float:
        if self.b <= x <= self.c:
            return 1.0
        if x <= self.a or x >= self.d:
            return 0.0
        if x < self.b:
            return _r((x - self.a) / (self.b - self.a))
        return _r((self.d - x) / (self.d - self.c))

    def describir(self) -> str:
        if self.nombre_forma == "gamma_lineal":
            return f"Γ({_fmt(self.a)}; {_fmt(self.b)})"
        if self.nombre_forma == "l_lineal":
            return f"L({_fmt(self.c)}; {_fmt(self.d)})"
        if self.nombre_forma == "triangular":
            return f"triangular({_fmt(self.a)}; {_fmt(self.b)}; {_fmt(self.d)})"
        return f"trap({_fmt(self.a)}; {_fmt(self.b)}; {_fmt(self.c)}; {_fmt(self.d)})"


def triangular(a: float, m: float, b: float) -> Trapezoidal:
    return Trapezoidal(a, m, m, b, "triangular")


def gamma_lineal(a: float, m: float) -> Trapezoidal:
    return Trapezoidal(a, m, math.inf, math.inf, "gamma_lineal")


def l_lineal(a: float, m: float) -> Trapezoidal:
    return Trapezoidal(-math.inf, -math.inf, a, m, "l_lineal")


@dataclass(frozen=True, slots=True)
class FuncionS:
    """Función S cuadrática por tramos; creciente = S, decreciente = Z."""

    a: float
    m: float
    b: float
    decreciente: bool = False

    def _s(self, x: float) -> float:
        if x <= self.a:
            return 0.0
        if x >= self.b:
            return 1.0
        ancho = self.b - self.a
        if x <= self.m:
            return 2.0 * ((x - self.a) / ancho) ** 2
        return 1.0 - 2.0 * ((x - self.b) / ancho) ** 2

    def grado(self, x: float) -> float:
        valor = self._s(x)
        return _r(1.0 - valor if self.decreciente else valor)

    def describir(self) -> str:
        return f"{'Z' if self.decreciente else 'S'}({_fmt(self.a)}; {_fmt(self.m)}; {_fmt(self.b)})"


@dataclass(frozen=True, slots=True)
class Gaussiana:
    m: float
    k: float

    def grado(self, x: float) -> float:
        return _r(math.exp(-self.k * (x - self.m) ** 2))

    def describir(self) -> str:
        return f"gaussiana(m = {_fmt(self.m)}; k = {_fmt(self.k)})"


@dataclass(frozen=True, slots=True)
class Singleton:
    a: float

    def grado(self, x: float) -> float:
        return 1.0 if x == self.a else 0.0

    def describir(self) -> str:
        return f"singleton({_fmt(self.a)})"


def _fmt(valor: float) -> str:
    if math.isinf(valor):
        return "∞" if valor > 0 else "-∞"
    return format(Decimal(str(valor)).normalize(), "f")


# ---------------------------------------------------------------------------
# Partición anclada a umbrales publicados
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Corte:
    """Un umbral publicado con su rampa de transición.

    `lado_seguro` indica dónde se coloca la rampa: INFERIOR la pone en
    [umbral - ancho, umbral], de modo que el término superior alcanza μ = 1
    exactamente en el umbral; SUPERIOR la pone en [umbral, umbral + ancho].
    `umbral_en` decide a qué término pertenece el propio umbral cuando ancho = 0,
    y reproduce así el operador nítido original.
    """

    umbral: float
    ancho: float
    lado_seguro: str
    umbral_en: str

    @property
    def izquierda(self) -> float:
        return self.umbral - self.ancho if self.lado_seguro == INFERIOR else self.umbral

    @property
    def derecha(self) -> float:
        return self.umbral if self.lado_seguro == INFERIOR else self.umbral + self.ancho

    def subida(self, x: float) -> float:
        """Pertenencia al término situado por encima del corte."""
        if self.ancho > 0:
            if x <= self.izquierda:
                return 0.0
            if x >= self.derecha:
                return 1.0
            return _r((x - self.izquierda) / (self.derecha - self.izquierda))
        if x > self.umbral:
            return 1.0
        if x < self.umbral:
            return 0.0
        return 1.0 if self.umbral_en == SUPERIOR else 0.0


@dataclass(frozen=True, slots=True)
class TerminoParticion:
    """Término j de una partición: sube en el corte j-1 y baja en el corte j."""

    cortes: tuple[Corte, ...]
    indice: int

    def grado(self, x: float) -> float:
        sube = self.cortes[self.indice - 1].subida(x) if self.indice > 0 else 1.0
        baja = 1.0 - self.cortes[self.indice].subida(x) if self.indice < len(self.cortes) else 1.0
        return _r(min(sube, baja))

    def describir(self) -> str:
        izquierda = self.cortes[self.indice - 1] if self.indice > 0 else None
        derecha = self.cortes[self.indice] if self.indice < len(self.cortes) else None
        if izquierda is None and derecha is not None:
            return f"L({_fmt(derecha.izquierda)}; {_fmt(derecha.derecha)})"
        if derecha is None and izquierda is not None:
            return f"Γ({_fmt(izquierda.izquierda)}; {_fmt(izquierda.derecha)})"
        assert izquierda is not None and derecha is not None
        return (
            f"trap({_fmt(izquierda.izquierda)}; {_fmt(izquierda.derecha)}; "
            f"{_fmt(derecha.izquierda)}; {_fmt(derecha.derecha)})"
        )


@dataclass(frozen=True, slots=True)
class UnionParticion:
    """Términos contiguos j..k de una partición fusionados en uno solo.

    En una partición de Ruspini, "TEMPLADA o CALIDA" designa el término de la
    partición más gruesa que se obtiene al quitar el corte interno: sube en el
    corte j-1 y baja en el corte k. Su función coincide con la suma acotada
    mín(1, μ_j + ... + μ_k). El máximo de Zadeh, en cambio, formaría un valle de
    0,5 en la frontera interna (a 24 °C, "15–35 °C" valdría 0,5), lo que
    contradiría el anclaje: la condición nítida vale 1 en todo el intervalo.
    """

    cortes: tuple[Corte, ...]
    desde: int
    hasta: int

    def grado(self, x: float) -> float:
        sube = self.cortes[self.desde - 1].subida(x) if self.desde > 0 else 1.0
        baja = 1.0 - self.cortes[self.hasta].subida(x) if self.hasta < len(self.cortes) else 1.0
        return _r(min(sube, baja))

    def describir(self) -> str:
        izquierda = TerminoParticion(self.cortes, self.desde).describir()
        derecha = TerminoParticion(self.cortes, self.hasta).describir()
        return izquierda if self.desde == self.hasta else f"{izquierda} ∪ {derecha} (fusionados)"


# ---------------------------------------------------------------------------
# Variables lingüísticas
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VariableLinguistica:
    """Variable de entrada o relación difusa sobre una diferencia de datos."""

    nombre: str
    unidad: str
    universo: tuple[float, float]
    fuente: str
    argumentos: tuple[str, ...]
    terminos: Mapping[str, FuncionPertenencia]
    descripcion: str = ""

    @property
    def campos(self) -> tuple[str, ...]:
        return self.argumentos if self.fuente in {"dato", "diferencia"} else ()

    def grado(self, termino: str, x: float) -> float:
        return self.terminos[termino].grado(x)

    def grado_union(self, terminos: Sequence[str], x: float) -> float:
        """Pertenencia a una etiqueta compuesta "T1 o T2 o ...".

        Los términos contiguos de una misma partición se fusionan (UnionParticion);
        los bloques no contiguos, y los términos de forma libre, se unen por el
        máximo de Zadeh.
        """
        indices: list[int] = []
        libres: list[str] = []
        cortes: tuple[Corte, ...] | None = None
        for termino in terminos:
            funcion = self.terminos[termino]
            if isinstance(funcion, TerminoParticion):
                cortes = funcion.cortes
                indices.append(funcion.indice)
            else:
                libres.append(termino)
        grados = [self.terminos[t].grado(x) for t in libres]
        if cortes is not None:
            bloques: list[list[int]] = []
            for indice in sorted(set(indices)):
                if bloques and indice == bloques[-1][-1] + 1:
                    bloques[-1].append(indice)
                else:
                    bloques.append([indice])
            grados += [UnionParticion(cortes, b[0], b[-1]).grado(x) for b in bloques]
        return max(grados, default=0.0)

    def fuzzificar(self, x: float) -> dict[str, float]:
        return {nombre: funcion.grado(x) for nombre, funcion in self.terminos.items()}


@dataclass(frozen=True, slots=True)
class Banda:
    hasta: float
    decision: str
    rama: str
    requiere: Mapping[str, Any] | None = None
    si_no: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class VariableSalida:
    nombre: str
    universo: tuple[float, float]
    terminos: Mapping[str, FuncionPertenencia]
    puntos: int
    abscisas: tuple[float, ...] = field(default=(), repr=False)
    muestras: Mapping[str, tuple[float, ...]] = field(default_factory=dict, repr=False)

    @classmethod
    def crear(
        cls, nombre: str, universo: tuple[float, float], terminos: Mapping[str, FuncionPertenencia], puntos: int
    ) -> "VariableSalida":
        inicio, fin = universo
        paso = (fin - inicio) / (puntos - 1)
        abscisas = tuple(inicio + i * paso for i in range(puntos))
        muestras = {t: tuple(f.grado(y) for y in abscisas) for t, f in terminos.items()}
        return cls(nombre, universo, terminos, puntos, abscisas, muestras)

    def agregar(self, alturas: Mapping[str, float]) -> tuple[float, ...]:
        """Implicación de Mamdani (recorte al nivel α) y unión por máximo."""
        activas = [(self.muestras[t], h) for t, h in alturas.items() if h > 0 and t in self.muestras]
        if not activas:
            return tuple(0.0 for _ in self.abscisas)
        return tuple(
            max(min(h, muestra[i]) for muestra, h in activas) for i in range(len(self.abscisas))
        )

    def centroide(self, alturas: Mapping[str, float]) -> float | None:
        """y* = Σ y·μ(y) / Σ μ(y) sobre el universo discretizado; None si B′ = ∅."""
        agregado = self.agregar(alturas)
        area = sum(agregado)
        if area <= 0:
            return None
        return round(sum(y * mu for y, mu in zip(self.abscisas, agregado)) / area, 3)


@dataclass(frozen=True, slots=True)
class ModeloDifuso:
    teoria: Mapping[str, str]
    variables: Mapping[str, VariableLinguistica]
    salida: VariableSalida
    consecuente_por_solicitud: Mapping[str, str]
    bandas: tuple[Banda, ...]
    severidad: Mapping[str, int]
    degradacion: Mapping[str, str]
    corte_degradacion: float

    def banda(self, indice: float) -> Banda:
        for banda in self.bandas:
            if indice < banda.hasta:
                return banda
        return self.bandas[-1]

    def mas_severa(self, a: str, b: str) -> str:
        return b if self.severidad.get(b, 0) > self.severidad.get(a, 0) else a


# ---------------------------------------------------------------------------
# Resultados de la inferencia difusa
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Pertenencia:
    variable: str
    termino: str
    valor: float | None
    unidad: str
    grado: float


@dataclass(frozen=True, slots=True)
class SalidaDifusa:
    variable: str
    alturas: tuple[tuple[str, float], ...]
    metodo: str
    indice: float | None
    banda: str | None
    decision_indice: str | None


@dataclass(frozen=True, slots=True)
class InferenciaDifusa:
    pertenencias: tuple[Pertenencia, ...]
    salida: SalidaDifusa
    origen_decision: str
    borrosidad: float | None


# ---------------------------------------------------------------------------
# Medidas difusas
# ---------------------------------------------------------------------------


def borrosidad(grados: Sequence[float]) -> float | None:
    """Borrosidad normalizada: 2/n · Σ |μ - μ*|, con μ* umbralizado en 0,5.

    Es fuzz(A) = d(A, A*) con distancia de Hamming relativa, escalada a [0, 1]:
    0 si todos los grados son 0 o 1, 1 si todos valen 0,5.
    """
    if not grados:
        return None
    distancia = sum(abs(g - (1.0 if g >= 0.5 else 0.0)) for g in grados)
    return round(2.0 * distancia / len(grados), 4)


def distancia_tchebychev(
    f: FuncionPertenencia, g: FuncionPertenencia, universo: tuple[float, float], puntos: int = 1001
) -> float:
    """d∞(A, B) = máx |μA(x) - μB(x)| sobre el universo discretizado."""
    inicio, fin = universo
    paso = (fin - inicio) / (puntos - 1)
    return round(max(abs(f.grado(inicio + i * paso) - g.grado(inicio + i * paso)) for i in range(puntos)), 6)


# ---------------------------------------------------------------------------
# Construcción y validación desde la base de conocimiento
# ---------------------------------------------------------------------------


def _numero(valor: Any, parametros: Mapping[str, Any], ruta: str, errores: list[str]) -> float | None:
    if isinstance(valor, Mapping) and "param" in valor:
        nombre = valor["param"]
        if nombre not in parametros:
            errores.append(f"{ruta}: parámetro desconocido '{nombre}'")
            return None
        return float(parametros[nombre].valor)
    if isinstance(valor, bool) or valor is None:
        errores.append(f"{ruta}: se esperaba un número o {{param: ...}}")
        return None
    try:
        return float(Decimal(str(valor)))
    except (ArithmeticError, ValueError):
        errores.append(f"{ruta}: número no válido '{valor}'")
        return None


def _funcion(forma: Mapping[str, Any], parametros: Mapping[str, Any], ruta: str, errores: list[str]) -> FuncionPertenencia | None:
    if not isinstance(forma, Mapping) or len(forma) != 1:
        errores.append(f"{ruta}: la función de pertenencia debe tener exactamente una forma")
        return None
    tipo, argumentos = next(iter(forma.items()))
    if tipo == "gaussiana":
        if not isinstance(argumentos, Mapping) or set(argumentos) != {"m", "k"}:
            errores.append(f"{ruta}: gaussiana requiere 'm' y 'k'")
            return None
        m = _numero(argumentos["m"], parametros, f"{ruta}.m", errores)
        k = _numero(argumentos["k"], parametros, f"{ruta}.k", errores)
        if m is None or k is None:
            return None
        if k <= 0:
            errores.append(f"{ruta}: gaussiana requiere k > 0")
            return None
        return Gaussiana(m, k)
    if tipo == "singleton":
        a = _numero(argumentos, parametros, ruta, errores)
        return Singleton(a) if a is not None else None
    if not isinstance(argumentos, list):
        errores.append(f"{ruta}: '{tipo}' requiere una lista de puntos")
        return None
    puntos = [_numero(v, parametros, f"{ruta}[{i}]", errores) for i, v in enumerate(argumentos)]
    if any(p is None for p in puntos):
        return None
    valores = [p for p in puntos if p is not None]
    esperados = {"triangular": 3, "trapezoidal": 4, "gamma_lineal": 2, "l_lineal": 2, "s": 3, "z": 3}
    if tipo not in esperados:
        errores.append(f"{ruta}: forma de pertenencia desconocida '{tipo}'")
        return None
    if len(valores) != esperados[tipo]:
        errores.append(f"{ruta}: '{tipo}' requiere {esperados[tipo]} puntos")
        return None
    if tipo == "triangular":
        a, m, b = valores
        if not a < m < b:
            errores.append(f"{ruta}: triangular exige a < m < b")
            return None
        return triangular(a, m, b)
    if tipo == "trapezoidal":
        a, b, c, d = valores
        if not a <= b <= c <= d:
            errores.append(f"{ruta}: trapezoidal exige a <= b <= c <= d")
            return None
        return Trapezoidal(a, b, c, d)
    if tipo in {"gamma_lineal", "l_lineal"}:
        a, m = valores
        if not a < m:
            errores.append(f"{ruta}: {tipo} exige a < m")
            return None
        return gamma_lineal(a, m) if tipo == "gamma_lineal" else l_lineal(a, m)
    a, m, b = valores
    if not a < m < b or abs(m - (a + b) / 2) > 1e-9:
        errores.append(f"{ruta}: la función {tipo.upper()} exige a < m < b con m = (a + b) / 2")
        return None
    return FuncionS(a, m, b, decreciente=tipo == "z")


def _normalizada(funcion: FuncionPertenencia, universo: tuple[float, float], puntos: int = 2001) -> bool:
    inicio, fin = universo
    paso = (fin - inicio) / (puntos - 1)
    candidatos = [inicio + i * paso for i in range(puntos)]
    if isinstance(funcion, Trapezoidal):
        candidatos += [v for v in (funcion.b, funcion.c) if not math.isinf(v)]
    if isinstance(funcion, (Gaussiana, Singleton)):
        candidatos.append(funcion.m if isinstance(funcion, Gaussiana) else funcion.a)
    if isinstance(funcion, TerminoParticion):
        candidatos += [c.umbral for c in funcion.cortes] + [c.izquierda for c in funcion.cortes]
        candidatos += [c.derecha for c in funcion.cortes]
    return max(funcion.grado(x) for x in candidatos) >= 1.0


def _variable(
    nombre: str, datos: Mapping[str, Any], parametros: Mapping[str, Any], errores: list[str]
) -> VariableLinguistica | None:
    ruta = f"inferencia_difusa.variables.{nombre}"
    if not isinstance(datos, Mapping):
        errores.append(f"{ruta}: se esperaba un mapeo")
        return None
    fuente = datos.get("fuente")
    if not isinstance(fuente, Mapping) or len(fuente) != 1 or next(iter(fuente)) not in FUENTES:
        errores.append(f"{ruta}.fuente: debe ser {{dato: campo}}, {{diferencia: [a, b]}} o {{calculo: nombre}}")
        return None
    tipo, argumento = next(iter(fuente.items()))
    argumentos = tuple(argumento) if isinstance(argumento, list) else (argumento,)
    if tipo == "diferencia" and len(argumentos) != 2:
        errores.append(f"{ruta}.fuente: diferencia requiere dos campos")
        return None
    if not all(isinstance(a, str) for a in argumentos):
        errores.append(f"{ruta}.fuente: los argumentos deben ser nombres")
        return None
    universo_datos = datos.get("universo")
    if not isinstance(universo_datos, list) or len(universo_datos) != 2:
        errores.append(f"{ruta}.universo: requiere [mínimo, máximo]")
        return None
    inicio = _numero(universo_datos[0], parametros, f"{ruta}.universo[0]", errores)
    fin = _numero(universo_datos[1], parametros, f"{ruta}.universo[1]", errores)
    if inicio is None or fin is None or not inicio < fin:
        errores.append(f"{ruta}.universo: debe ser un intervalo creciente")
        return None
    universo = (inicio, fin)

    terminos: dict[str, FuncionPertenencia] = {}
    if "cortes" in datos:
        nombres = datos.get("terminos")
        cortes_datos = datos["cortes"]
        if not isinstance(cortes_datos, list) or not cortes_datos or not isinstance(nombres, list):
            errores.append(f"{ruta}: una partición requiere 'cortes' y la lista 'terminos'")
            return None
        if len(nombres) != len(cortes_datos) + 1 or len(set(nombres)) != len(nombres):
            errores.append(f"{ruta}: una partición con n cortes requiere n + 1 términos distintos")
            return None
        cortes: list[Corte] = []
        for i, corte in enumerate(cortes_datos):
            ruta_corte = f"{ruta}.cortes[{i}]"
            umbral = _numero(corte.get("umbral"), parametros, f"{ruta_corte}.umbral", errores)
            ancho = _numero(corte.get("ancho", 0), parametros, f"{ruta_corte}.ancho", errores)
            lado = corte.get("lado_seguro")
            umbral_en = corte.get("umbral_en")
            if lado not in {INFERIOR, SUPERIOR} or umbral_en not in {INFERIOR, SUPERIOR}:
                errores.append(f"{ruta_corte}: 'lado_seguro' y 'umbral_en' deben ser INFERIOR o SUPERIOR")
                return None
            if umbral is None or ancho is None:
                return None
            if ancho < 0:
                errores.append(f"{ruta_corte}: el ancho de transición no puede ser negativo")
                return None
            cortes.append(Corte(umbral, ancho, lado, umbral_en))
        for previo, siguiente in zip(cortes, cortes[1:]):
            if not previo.umbral < siguiente.umbral:
                errores.append(f"{ruta}: los cortes deben estar ordenados por umbral creciente")
                return None
            if previo.derecha > siguiente.izquierda:
                errores.append(
                    f"{ruta}: las rampas de {previo.umbral} y {siguiente.umbral} se solapan; "
                    f"reduzca el ancho de transición"
                )
                return None
        tupla = tuple(cortes)
        for j, termino in enumerate(nombres):
            terminos[str(termino)] = TerminoParticion(tupla, j)
    elif isinstance(datos.get("terminos"), Mapping):
        for termino, forma in datos["terminos"].items():
            funcion = _funcion(forma, parametros, f"{ruta}.terminos.{termino}", errores)
            if funcion is not None:
                terminos[str(termino)] = funcion
    else:
        errores.append(f"{ruta}: requiere 'cortes' + 'terminos' o un mapeo de términos")
        return None

    for termino, funcion in terminos.items():
        if not _normalizada(funcion, universo):
            errores.append(f"{ruta}.terminos.{termino}: el conjunto no es normalizado (altura < 1)")
    return VariableLinguistica(
        nombre=nombre,
        unidad=str(datos.get("unidad", "")),
        universo=universo,
        fuente=tipo,
        argumentos=argumentos,
        terminos=terminos,
        descripcion=str(datos.get("descripcion", "")),
    )


def construir_modelo(
    config: Mapping[str, Any],
    parametros: Mapping[str, Any],
    solicitudes: Sequence[str],
    decisiones: Sequence[str],
    errores: list[str],
) -> ModeloDifuso | None:
    """Valida la sección `inferencia_difusa`. Los errores se acumulan en `errores`."""
    inicio_errores = len(errores)
    teoria = dict(config.get("teoria", {}))
    for clave, admitidos in TEORIA_ADMITIDA.items():
        valor = teoria.get(clave)
        if valor not in admitidos:
            errores.append(
                f"inferencia_difusa.teoria.{clave}: '{valor}' no admitido; el motor implementa {sorted(admitidos)}"
            )

    variables: dict[str, VariableLinguistica] = {}
    for nombre, datos in dict(config.get("variables", {})).items():
        variable = _variable(str(nombre), datos, parametros, errores)
        if variable is not None:
            variables[str(nombre)] = variable

    datos_salida = config.get("variable_salida")
    salida: VariableSalida | None = None
    if not isinstance(datos_salida, Mapping):
        errores.append("inferencia_difusa.variable_salida: requerida")
    else:
        nombre_salida = str(datos_salida.get("nombre", "severidad"))
        universo_salida = datos_salida.get("universo", [0, 100])
        puntos = int(config.get("puntos", 1001))
        if puntos < 101:
            errores.append("inferencia_difusa.puntos: se requieren al menos 101 puntos")
        terminos: dict[str, FuncionPertenencia] = {}
        for termino, forma in dict(datos_salida.get("terminos", {})).items():
            funcion = _funcion(forma, parametros, f"inferencia_difusa.variable_salida.{termino}", errores)
            if funcion is not None:
                terminos[str(termino)] = funcion
        if not terminos:
            errores.append("inferencia_difusa.variable_salida: requiere términos")
        else:
            rango = (float(universo_salida[0]), float(universo_salida[1]))
            for termino, funcion in terminos.items():
                if not _normalizada(funcion, rango):
                    errores.append(f"inferencia_difusa.variable_salida.{termino}: no es normalizado")
            salida = VariableSalida.crear(nombre_salida, rango, terminos, max(puntos, 101))

    consecuentes = {str(k): str(v) for k, v in dict(config.get("consecuente_por_solicitud", {})).items()}
    for solicitud, termino in consecuentes.items():
        if solicitud not in solicitudes:
            errores.append(f"inferencia_difusa.consecuente_por_solicitud: solicitud desconocida '{solicitud}'")
        if salida is not None and termino not in salida.terminos:
            errores.append(f"inferencia_difusa.consecuente_por_solicitud: término de salida desconocido '{termino}'")

    bandas: list[Banda] = []
    anterior = -math.inf
    for i, datos in enumerate(config.get("bandas", [])):
        ruta = f"inferencia_difusa.bandas[{i}]"
        hasta = _numero(datos.get("hasta"), parametros, f"{ruta}.hasta", errores)
        decision = datos.get("decision")
        rama = datos.get("rama")
        if decision not in decisiones or not isinstance(rama, str):
            errores.append(f"{ruta}: requiere una decisión conocida y su rama")
            continue
        if hasta is None or hasta <= anterior:
            errores.append(f"{ruta}: las bandas deben tener límites crecientes")
            continue
        anterior = hasta
        si_no = datos.get("si_no")
        alternativa: tuple[str, str] | None = None
        if si_no is not None:
            if si_no.get("decision") not in decisiones or not isinstance(si_no.get("rama"), str):
                errores.append(f"{ruta}.si_no: requiere una decisión conocida y su rama")
                continue
            alternativa = (str(si_no["decision"]), str(si_no["rama"]))
        bandas.append(Banda(hasta, str(decision), rama, datos.get("requiere"), alternativa))
    if not bandas:
        errores.append("inferencia_difusa.bandas: requiere al menos una banda")
    elif salida is not None and bandas[-1].hasta < salida.universo[1]:
        errores.append("inferencia_difusa.bandas: la última banda debe cubrir el universo de salida")

    severidad = {str(k): int(v) for k, v in dict(config.get("severidad_decisiones", {})).items()}
    faltan = sorted(set(decisiones) - set(severidad))
    if faltan:
        errores.append(f"inferencia_difusa.severidad_decisiones: faltan {faltan}")

    datos_degradacion = dict(config.get("degradacion", {}))
    degradacion = {str(k): str(v) for k, v in dict(datos_degradacion.get("solicitudes", {})).items()}
    for origen, destino in degradacion.items():
        if origen not in solicitudes or destino not in solicitudes:
            errores.append(f"inferencia_difusa.degradacion: solicitud desconocida en {origen} → {destino}")
    corte = _numero(datos_degradacion.get("corte", 1), parametros, "inferencia_difusa.degradacion.corte", errores)
    if corte is not None and not 0 < corte <= 1:
        errores.append("inferencia_difusa.degradacion.corte: un corte-α debe estar en (0, 1]")

    if len(errores) > inicio_errores or salida is None or corte is None:
        return None
    return ModeloDifuso(
        teoria=teoria,
        variables=variables,
        salida=salida,
        consecuente_por_solicitud=consecuentes,
        bandas=tuple(bandas),
        severidad=severidad,
        degradacion=degradacion,
        corte_degradacion=corte,
    )


__all__ = [
    "Banda", "Corte", "FuncionPertenencia", "FuncionS", "Gaussiana", "InferenciaDifusa",
    "ModeloDifuso", "Pertenencia", "SalidaDifusa", "Singleton", "TerminoParticion", "Trapezoidal",
    "UnionParticion",
    "VariableLinguistica", "VariableSalida", "borrosidad", "construir_modelo", "distancia_tchebychev",
    "gamma_lineal", "l_lineal", "triangular",
]
