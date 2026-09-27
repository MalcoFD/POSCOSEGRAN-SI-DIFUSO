# Base de conocimiento

Copia versionada del material de dominio y el catálogo que carga el backend.

| Archivo | Contenido |
|---|---|
| `POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md` | Base 3.1: reglas R01–R52, parámetros, tablas, R30, casos C01–C40 y, en la sección 13, el **modelo difuso** (variables lingüísticas, anclaje, cortes-α, índice de severidad) |
| `base_conocimiento.yaml` | **Base operativa que ejecuta el motor**: reglas SI–ENTONCES, parámetros, definiciones, tabla de tiempo, datos exigibles, resolución R30, restricciones de integridad y la sección `inferencia_difusa` (sistema Mamdani) |
| `catalogo.yaml` | Texto documental de las reglas, las nueve ramas y las fuentes (se mantiene a mano; ver abajo) |
| `casos_referencia.json` | 242 casos congelados (C01–C40 y variaciones) con lo que decide la base 3.1, incluido el índice de severidad; para regresión y para medir el impacto de un cambio |
| `casos_referencia_nitida.json` | Los mismos 242 casos con lo que decidía la base nítida 2.0: la prueba de que la base difusa con anchos nulos la reproduce |
| `POSCOSEGRAN_informe_impacto_difuso.md` | Impacto de la migración a lógica difusa: casos que cambian, sensibilidad a δ y verificaciones |

## Dos archivos, una versión

`base_conocimiento.yaml` es lo que el motor ejecuta; `catalogo.yaml` es el texto
del documento que ve el usuario. Se versionan y se cargan juntos, y el cargador
exige que describan exactamente las mismas reglas, ramas y fuentes: la pantalla de
conocimiento nunca muestra una regla distinta de la que se aplicó.

```bash
# Validar y registrar la versión (semilla) como activa
python -m poscosegran.conocimiento.cargar knowledge --activar
```

> **No ejecutar `scripts/transcribir_base.py`.** Sobrescribe `catalogo.yaml` con
> cabeceras fijas (2.0/1.0/0.7.0) y sin la redacción revisada de R31–R52 y de los
> antecedentes difusos. Mientras no se actualice, `catalogo.yaml` se mantiene a
> mano junto con el documento de 52 reglas; el cargador comprueba igualmente que
> ambos describan las mismas reglas.

Si la base no es válida, el cargador lista los errores y no registra nada. Volver
a cargar el mismo contenido no duplica la versión: se identifica por su huella
SHA-256. Cada evaluación queda ligada por `id_version_conocimiento` a la versión
con la que se resolvió.

## Cambiar el conocimiento

En un entorno en marcha, los cambios se hacen desde el **módulo de adquisición**
(pantalla *Adquisición*, rol `INGENIERO_CONOCIMIENTO`): la propuesta se valida, se
mide contra los casos de referencia y las evaluaciones recientes, y se activa como
versión nueva. Las evaluaciones ya emitidas conservan su versión.

Editar este archivo a mano también es válido para la semilla; después:

```bash
cd backend && pytest tests/test_base_conocimiento.py tests/casos
```

Si un cambio intencional altera decisiones, `test_casos_de_referencia_se_reproducen`
fallará: revisa los casos afectados y congela el nuevo comportamiento sobre los
mismos casos con `python scripts/generar_casos_referencia.py --reevaluar`. Sin
opciones, el script vuelve a muestrear variaciones y cambia el conjunto de casos.

## Modelo difuso

Los anchos de transición (`transicion_*`) y los cortes-α (`corte_*`) son
parámetros de la base: se ajustan desde el módulo de adquisición como cualquier
umbral, y la propuesta muestra los casos que cambian y la mayor variación del
índice de severidad (distancia de Tchebychev). Con todos los anchos a 0 la base
se comporta exactamente como la nítida 2.0 (`tests/casos/nitida.py`).

## Lo que la base deja abierto

El propio documento lo enumera en su sección 11 y el motor lo respeta en lugar
de rellenarlo:

- Los límites transferidos de maíz amarillo duro y de criterios comerciales no
  están validados para chulpi.
- La tabla de tiempo de referencia es de cereales NDSU, con celdas sin duración
  publicada. El motor avanza a una celda numérica más exigente y registra la
  sustitución; nunca interpola ni extrapola.
- No existe todavía una tabla de humedad de equilibrio que cubra el clima
  altoandino. Mientras no se cargue, `humedad_equilibrio_maiz` llega como
  observación y, sin ella, R10 y R11 no recomiendan aireación.
- Los casos C01–C40 son expectativas de aceptación, no ensayos de campo.
