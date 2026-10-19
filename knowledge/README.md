# Conocimiento de POSCOSEGRAN

La semilla vigente está en `difuso/`: base 5.0, motor Mamdani 3.0.0-mamdani. Conserva la cobertura R01–R52; el primer nivel tiene 4 mediciones y 9 reglas, y el nivel de decisión final tiene 11 antecedentes y 14 reglas. Las condiciones críticas están en los antecedentes que excluyen conclusiones permisivas.

Los YAML de esta carpeta raíz y `casos_referencia.json` conservan la base determinista 2.0 y las 242 expectativas históricas. No deben sobrescribirse para ocultar diferencias. Los documentos de 30 reglas son antecedentes; la especificación ampliada es `POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md`.

- Curvas vigentes: `difuso/base_conocimiento.yaml`, sección `difuso`.
- Fuentes y reglas: `difuso/catalogo.yaml`.
- Explicación y consecuencias: [conversión](../docs/CONVERSION_DIFUSA.md).
- Generador de la semilla: `backend/scripts/generar_modelo_difuso.py`; modificar conocimiento activo requiere otra versión y revisión de impacto.

La carga sin ruta explícita selecciona la semilla difusa. Para mantener una versión antigua, indicar su carpeta explícitamente. Las evaluaciones emitidas conservan su contenido y su hash.

El primer nivel tiene cuatro entradas (tres aplicables en hermético) y una salida conjunta. `historico_mamdani_3_1/` y `historico_mamdani_4_0/` conservan las semillas anteriores; no son activas.
