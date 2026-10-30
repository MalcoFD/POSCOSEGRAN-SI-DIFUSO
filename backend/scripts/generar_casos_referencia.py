"""Congela las 320 anclas de las matrices vigentes y cuatro corridas simuladas."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import json
from poscosegran.dominio.hechos import Instantanea, Modalidad, Fase
from poscosegran.dominio.valores import Conjunto, Dato, EstadoDato
from poscosegran.dominio.motor import evaluar
from poscosegran.inferencia.base_conocimiento import cargar
from poscosegran.inferencia import serializacion

RAIZ = Path(__file__).resolve().parents[2]
BASE = cargar()
M = BASE.contenido["operativa"]["difuso"]
AHORA = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ANCLAS = {
    "humedad_grano": [12, 12.75, 13.75, 15],
    "temperatura_grano": [10, 20, 25, 35],
    "hr_almacen": [45, 55, 60, 75],
}


def instantanea(modalidad, valores, ahora=AHORA):
    valores = dict(valores)
    if modalidad == "HERMETICO":
        valores.update(estado_barrera="INTEGRA", procedimiento_interno="SENSOR_INTERNO")
    datos = {
        k: Dato(
            campo=k,
            estado=EstadoDato.VALIDO,
            valor=v if isinstance(v, str) else Decimal(str(v)),
            unidad="TEXTO"
            if isinstance(v, str)
            else "PCT_BH"
            if k == "humedad_grano"
            else "PCT_HR"
            if k == "hr_almacen"
            else "CELSIUS",
            fecha_observacion=ahora,
            metodo="INSPECCION" if isinstance(v, str) else "INSTRUMENTAL",
            evidencia="Caso simulado: muestra representativa e inspección documentadas.",
        )
        for k, v in valores.items()
    }
    return Instantanea(
        fecha_evaluacion=ahora,
        fase=Fase.INGRESO,
        tipo_almacenamiento=Modalidad(modalidad),
        datos=Conjunto(datos),
    )


def main():
    casos = []
    for mod, matriz in M["matrices"].items():
        for r in matriz["reglas"]:
            valores = {}
            for h in r["si"]["todos"]:
                k, t = h["entrada"], h["conjunto"]
                valores[k] = (
                    t
                    if k == "estado_fisico_sanitario"
                    else ANCLAS[k][list(M["entradas"][k]["conjuntos"]).index(t)]
                )
            i = instantanea(mod, valores)
            res = evaluar(i, BASE)
            x = res.difuso["decision"]
            casos.append(
                {
                    "id": "ancla:" + r["id"],
                    "hechos": serializacion.comprimir(serializacion.a_json(i), {}),
                    "esperado": {
                        "decision": res.decision_final,
                        "centroide": x["centroide"],
                        "reglas": list(res.reglas_activadas),
                    },
                }
            )
    contenido = {
        "version_base": BASE.version_base,
        "version_parametros": BASE.version_parametros,
        "hash_base": BASE.hash,
        "plantilla_datos": {},
        "casos": casos,
    }
    (RAIZ / "knowledge/casos_referencia.json").write_text(
        json.dumps(contenido, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    corridas = []
    for ident, titulo, mod, h, t, hr, s in [
        (
            "M320-L01",
            "Conservación favorable en hermético",
            "HERMETICO",
            12,
            10,
            None,
            "SIN_HALLAZGOS",
        ),
        (
            "M320-L02",
            "Transición térmica y vigilancia",
            "NO_HERMETICO",
            12,
            18,
            50,
            "SIN_HALLAZGOS",
        ),
        (
            "M320-L03",
            "Concurrencia de condiciones adversas",
            "NO_HERMETICO",
            13.5,
            25,
            60,
            "SIN_HALLAZGOS",
        ),
        ("M320-L04", "Hallazgo sanitario crítico", "NO_HERMETICO", 12, 10, 50, "HALLAZGO_CRITICO"),
    ]:
        valores = {"humedad_grano": h, "temperatura_grano": t, "estado_fisico_sanitario": s}
        if hr is not None:
            valores["hr_almacen"] = hr
        r = evaluar(instantanea(mod, valores), BASE)
        x = r.difuso["decision"]
        corridas.append(
            {
                "id": ident,
                "titulo": titulo,
                "modalidad": mod,
                "valores": valores,
                "decision": r.decision_final,
                "centroide": x["centroide"],
                "reglas_activadas": list(r.reglas_activadas),
                "detalle": x,
            }
        )
    (RAIZ / "knowledge/corridas_4.json").write_text(
        json.dumps(corridas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(casos)} anclas y {len(corridas)} corridas generadas.")


if __name__ == "__main__":
    main()
