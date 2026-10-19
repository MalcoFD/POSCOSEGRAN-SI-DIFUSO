"""Compara los casos congelados sin modificar sus expectativas históricas."""
import json
import argparse
from collections import Counter
from pathlib import Path

from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia.adquisicion import cargar_casos_referencia
from poscosegran.inferencia.base_conocimiento import cargar, ruta_por_defecto


def comparar(anterior: str = '2.0') -> dict[str, object]:
    rutas = {
        '2.0': ruta_por_defecto(),
        '3.1': ruta_por_defecto() / 'historico_mamdani_3_1',
        '4.0': ruta_por_defecto() / 'historico_mamdani_4_0',
    }
    historica = cargar(rutas[anterior])
    difusa = cargar(ruta_por_defecto() / 'difuso')
    transiciones: Counter[str] = Counter()
    diferencias = []
    casos = cargar_casos_referencia()
    for ident, _, inst in casos:
        antes, despues = evaluar(inst, historica), evaluar(inst, difusa)
        if antes.decision_final == despues.decision_final:
            continue
        transiciones[f'{antes.decision_final} → {despues.decision_final}'] += 1
        diferencias.append({
            'caso': ident, 'antes': antes.decision_final, 'despues': despues.decision_final,
            'motivos_nuevos': [m.id for m in despues.motivos if m.id not in {a.id for a in antes.motivos}],
            'pendientes_nuevos': [p.campo for p in despues.datos_pendientes if p.campo not in {a.campo for a in antes.datos_pendientes}],
        })
    return {'comparados': len(casos), 'cambios': len(diferencias), 'version_anterior': historica.version_base, 'version': difusa.version_base,
            'transiciones': dict(transiciones), 'casos': diferencias}


if __name__ == '__main__':
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument('--anterior', choices=['2.0', '3.1', '4.0'], default='2.0')
    opciones = argumentos.parse_args()
    informe = comparar(opciones.anterior)
    nombre = f"comparacion_{opciones.anterior.replace('.', '_')}_a_5_0.json"
    salida = Path(__file__).resolve().parents[2] / 'test-results' / nombre
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Comparados {informe['comparados']}; diferencias {informe['cambios']}. Informe: {salida}")
