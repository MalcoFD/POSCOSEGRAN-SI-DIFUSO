"""La lógica de grados [inf, sup] extiende exactamente la de tres estados.

Sobre {[0,0], [1,1], [0,1], NO_APLICA} la t-norma mínimo, la t-conorma máximo y la
negación 1 - x coinciden con y(), o() y no() de Kleene. Sobre grados cualesquiera
se cumplen las leyes de (F(U), mín, máx, 1 - x): conmutatividad, asociatividad,
idempotencia, absorción, De Morgan e involución. No se cumplen el tercero excluido
ni la no contradicción, que es lo esperado en lógica difusa.
"""

from __future__ import annotations

import itertools

import pytest

from poscosegran.dominio.valores import (
    D,
    F,
    G_D,
    G_F,
    G_NA,
    G_V,
    NA,
    Grado,
    V,
    conjuncion,
    disyuncion,
    negacion,
    no,
    o,
    y,
)

TRES_ESTADOS = (V, F, D, NA)
VALORES = (0.0, 0.2, 0.5, 0.7, 1.0)
GRADOS = [Grado(a, b) for a, b in itertools.product(VALORES, VALORES) if a <= b] + [G_NA]


@pytest.mark.parametrize(("a", "b"), list(itertools.product(TRES_ESTADOS, TRES_ESTADOS)))
def test_conjuncion_y_disyuncion_coinciden_con_kleene(a, b) -> None:
    ga, gb = Grado.desde_tri(a), Grado.desde_tri(b)
    assert conjuncion(ga, gb).tri is y(a, b)
    assert disyuncion(ga, gb).tri is o(a, b)


@pytest.mark.parametrize("a", TRES_ESTADOS)
def test_negacion_coincide_con_kleene(a) -> None:
    assert negacion(Grado.desde_tri(a)).tri is no(a)


def test_constantes() -> None:
    assert (G_V.tri, G_F.tri, G_D.tri, G_NA.tri) == (V, F, D, NA)
    assert G_D.desconocido and not G_V.desconocido and not G_NA.desconocido
    assert Grado.exacto(0.6).tri is D  # un grado parcial no se afirma ni se niega en tres estados


def test_grado_mal_formado() -> None:
    with pytest.raises(ValueError):
        Grado(0.8, 0.3)


def _efectivos(*grados: Grado) -> bool:
    return not any(g.no_aplica for g in grados)


@pytest.mark.parametrize(("a", "b"), list(itertools.product(GRADOS, GRADOS)))
def test_de_morgan_conmutatividad_y_absorcion(a: Grado, b: Grado) -> None:
    assert negacion(conjuncion(a, b)) == disyuncion(negacion(a), negacion(b))
    assert negacion(disyuncion(a, b)) == conjuncion(negacion(a), negacion(b))
    assert conjuncion(a, b) == conjuncion(b, a)
    assert disyuncion(a, b) == disyuncion(b, a)
    if _efectivos(a, b):
        assert conjuncion(a, disyuncion(a, b)) == a
        assert disyuncion(a, conjuncion(a, b)) == a


@pytest.mark.parametrize("a", GRADOS)
def test_idempotencia_involucion_y_neutros(a: Grado) -> None:
    assert conjuncion(a, a) == a
    assert disyuncion(a, a) == a
    assert negacion(negacion(a)) == a
    if not a.no_aplica:
        assert conjuncion(a, G_V) == a
        assert disyuncion(a, G_F) == a
        assert conjuncion(a, G_NA) == a  # NO_APLICA no participa


def test_asociatividad() -> None:
    for a, b, c in itertools.product(GRADOS[:10], repeat=3):
        assert conjuncion(conjuncion(a, b), c) == conjuncion(a, conjuncion(b, c))
        assert disyuncion(disyuncion(a, b), c) == disyuncion(a, disyuncion(b, c))


def test_no_contradiccion_y_tercero_excluido_no_se_cumplen() -> None:
    medio = Grado.exacto(0.6)
    assert conjuncion(medio, negacion(medio)) == Grado.exacto(0.4)
    assert disyuncion(medio, negacion(medio)) == Grado.exacto(0.6)
    # la cota de Zadeh: A ∧ ¬A nunca supera 0,5
    for g in (Grado.exacto(v / 20) for v in range(21)):
        assert conjuncion(g, negacion(g)).sup <= 0.5


def test_la_negacion_no_crea_informacion() -> None:
    assert negacion(G_D) == G_D
    assert negacion(Grado(0.2, 0.7)) == Grado(0.3, 0.8)
