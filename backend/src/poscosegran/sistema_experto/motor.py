"""Resolución exacta únicamente para reproducir bases históricas 2.0–4.0."""
from ..inferencia.motor import Motor as Agenda, Resultado, VERSION_MOTOR
from ..inferencia.base_hechos import BaseHechos, EvaluacionRama
from ..inferencia.base_conocimiento import BaseConocimiento
from ..inferencia.lenguaje import Evaluador
from ..dominio.hechos import Motivo
from ..dominio.valores import V

__all__ = ['Motor', 'Resultado', 'VERSION_MOTOR', 'resolver']

def resolver(base: BaseConocimiento, hechos: BaseHechos, evaluador: Evaluador) -> tuple[str, str]:
    """Prioridad fija: gana la primera rama VERDADERO.

    Se evalúan todas las ramas para que la explicación pueda decir qué le
    faltó a cada autorización, aunque solo una emita la decisión.
    """
    elegida = None
    for rama in base.resolucion:
        juicio = evaluador.evaluar(rama.si)
        fallidas = () if juicio.valor is V else tuple(evaluador.fallidas(rama.si))
        hechos.ramas.append(
            EvaluacionRama(rama=rama.rama, decision=rama.decision, valor=juicio.valor.value, fallidas=fallidas)
        )
        if elegida is None and juicio.valor is V:
            elegida = rama
    assert elegida is not None, "la última rama se aplica siempre"
    if elegida.mensaje:
        hechos.motivos.append(
            Motivo(
                id=f"{elegida.rama}:SIN_CONCLUSION",
                regla=elegida.rama,
                mensaje=elegida.mensaje,
                fuentes=base.fuentes_de(elegida.rama),
                fundamento=base.fundamento_de(elegida.rama),
            )
        )
    return elegida.decision, elegida.rama

class Motor(Agenda):
    def _resolver(self, hechos: BaseHechos, evaluador: Evaluador) -> tuple[str, str]:
        return resolver(self.base, hechos, evaluador)
