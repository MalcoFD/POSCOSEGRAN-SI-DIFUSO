"""Centroide exacto de la envolvente máxima de conjuntos lineales recortados.

Integra por segmentos, añadiendo cruces entre consecuentes. No promedia los
centroides de las reglas: eso sería otro algoritmo. La curva también explica el cálculo.
"""

from collections.abc import Sequence

from .pertenencia import pertenencia


def centroide(
    conjuntos: Sequence[tuple[Sequence[float], float]],
) -> tuple[float, float, list[list[float]]] | None:
    # max(min(a, C), min(b, C)) = min(max(a,b), C): cada curva
    # consecuente se integra una sola vez, sin cambiar la envolvente.
    por_curva: dict[tuple[float, ...], float] = {}
    for puntos, alfa in conjuntos:
        if alfa > 0:
            clave = tuple(float(x) for x in puntos)
            por_curva[clave] = max(por_curva.get(clave, 0.0), alfa)
    activos = list(por_curva.items())
    if not activos:
        return None
    if any(not 0 < a <= 1 for _, a in activos):
        raise ValueError("Activación fuera de [0,1]")
    vertices: set[float] = set()
    for puntos, alfa in activos:
        p = list(map(float, puntos))
        vertices.update(p)
        for x0, x1 in zip(p, p[1:]):
            y0, y1 = pertenencia(x0, p), pertenencia(x1, p)
            if x1 > x0 and min(y0, y1) < alfa < max(y0, y1):
                vertices.add(x0 + (alfa - y0) * (x1 - x0) / (y1 - y0))
    cortes = sorted(vertices)
    for x0, x1 in zip(cortes, cortes[1:]):
        lineas = [(min(a, pertenencia(x0, p)), min(a, pertenencia(x1, p))) for p, a in activos]
        for i, (a0, a1) in enumerate(lineas):
            for b0, b1 in lineas[i + 1 :]:
                d0, d1 = a0 - b0, a1 - b1
                if d0 * d1 < 0:
                    vertices.add(x0 + (x1 - x0) * d0 / (d0 - d1))
    curva = [[x, max(min(a, pertenencia(x, p)) for p, a in activos)] for x in sorted(vertices)]
    area = momento = 0.0
    for (x0, y0), (x1, y1) in zip(curva, curva[1:]):
        ancho = x1 - x0
        # Fórmulas locales evitan cancelación al integrar potencias grandes.
        segmento = ancho * (y0 + y1) / 2
        area += segmento
        momento += x0 * segmento + ancho * ancho * (y0 + 2 * y1) / 6
    if area <= 1e-12:
        return None
    return momento / area, area, curva
