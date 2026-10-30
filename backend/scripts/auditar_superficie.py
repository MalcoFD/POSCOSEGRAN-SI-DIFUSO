"""Diagnóstico reproducible de la superficie continua de la FAM publicada."""
import json
from itertools import product
from pathlib import Path

from poscosegran.inferencia.base_conocimiento import cargar
from poscosegran.sistema_difuso.defuzzificacion import centroide
from poscosegran.sistema_difuso.pertenencia import pertenencia


def main():
    base = cargar()
    m = base.contenido['operativa']['difuso']
    grillas = {'humedad_grano': [11.5+i*.1 for i in range(36)],
               'temperatura_grano': [10+i for i in range(26)],
               'hr_almacen': [45+i for i in range(31)]}
    estados = m['entradas']['estado_fisico_sanitario']['dominio']
    resultados = []
    for modalidad, mat in m['matrices'].items():
        campos = mat['entradas'][:-1]
        valores = [grillas[c] for c in campos]
        inversas = cambios = comparaciones = muestras = 0
        mayor = 0.0
        ejemplo = None
        for estado in estados:
            reglas = [r for r in mat['reglas'] if r['si']['todos'][-1]['conjunto'] == estado]
            cache = {}
            for indices in product(*(range(len(v)) for v in valores)):
                mus = {c: {k: pertenencia(valores[i][indices[i]], p) for k,p in m['entradas'][c]['conjuntos'].items()} for i,c in enumerate(campos)}
                alfas = {}
                for r in reglas:
                    alfa = min(mus[h['entrada']][h['conjunto']] for h in r['si']['todos'][:-1])
                    alfas[r['entonces']] = max(alfas.get(r['entonces'], 0), alfa)
                z = centroide([(m['salidas'][k], a) for k,a in alfas.items() if a > 0])[0]
                clase = next(i for i,c in enumerate(m['clasificacion']) if z < c['hasta'])
                cache[indices] = (z, clase)
                muestras += 1
                for eje in range(len(indices)):
                    if indices[eje] == 0:
                        continue
                    previo = list(indices)
                    previo[eje] -= 1
                    anterior = cache[tuple(previo)]
                    comparaciones += 1
                    descenso = anterior[0] - z
                    if descenso > 1e-8:
                        inversas += 1
                    if clase < anterior[1]:
                        cambios += 1
                    if descenso > mayor:
                        mayor = descenso
                        ejemplo = {'estado': estado, 'eje': campos[eje], 'entrada': {c: valores[i][indices[i]] for i,c in enumerate(campos)}, 'antes': anterior[0], 'despues': z}
        resultados.append({'modalidad': modalidad, 'muestras': muestras, 'comparaciones': comparaciones,
                           'descensos_locales_indice': inversas, 'descenso_maximo': mayor,
                           'descensos_de_categoria': cambios, 'ejemplo_descenso_maximo': ejemplo})
    salida = {'hash_base': base.hash, 'grillas': grillas, 'resultados': resultados,
              'nota': 'Diagnóstico por malla finita, no demostración de monotonía global del centroide. MIN/MAX puede generar oscilaciones locales dentro de una categoría.'}
    destino = Path(__file__).resolve().parents[2] / 'test-results/superficie-mamdani.json'
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    assert all(r['descensos_de_categoria'] == 0 for r in resultados), 'La malla detectó una mejora de categoría al aumentar una entrada.'


if __name__ == '__main__':
    main()
