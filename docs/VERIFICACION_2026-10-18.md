> Informe histórico de la primera conversión 3.1. La verificación vigente de la base 5.0 está en VERIFICACION_MAMDANI_FINAL.md; el informe de 4.0 también es histórico.

# Verificación de los dos planes — 18 de octubre de 2026

## Resultado

Se implementó primero el núcleo Mamdani y su integración/versionado; después se completaron las correcciones del diagnóstico y la limpieza. La aplicación local queda en `http://localhost:8080`, con base **3.1**, motor **1.0.0-mamdani**, 52 reglas documentales, 20 módulos y 60 producciones difusas. El modelo histórico permanece disponible para reproducir las evaluaciones emitidas con él.

Las curvas y la política son parámetros explícitos del prototipo, con referencias y distinción de su fundamento. Se verificó su implementación matemática y funcional; no se afirma calibración agronómica ni certificación sanitaria.

## Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| Suite Python completa con PostgreSQL aislado | **211 aprobadas**, 1 omitida deliberadamente porque exige otra credencial; 224,92 s. |
| Prueba con cuenta restringida `poscosegran_app` | **1 aprobada**, sin permiso de DDL. Entre ambas ejecuciones quedan cubiertas las 212 pruebas existentes al cierre. |
| Pruebas nuevas del núcleo y regresiones | Incluyen pertenencias, hombros, centroide analítico y contraste con integración independiente, dominio/cobertura, datos desconocidos, prioridades, riesgo, persistencia, adquisición y autorización con plan. |
| C01–C40 y 242 casos congelados | Expectativas históricas conservadas; regresión aprobada con el motor histórico. |
| Comparación histórica frente a Mamdani 3.1 | 67 diferencias documentadas; cero nuevas autorizaciones. |
| Ruff | Sin errores en fuentes, scripts y pruebas. |
| Mypy estricto | Sin errores en 67 archivos. |
| ESLint y TypeScript, incluido control de símbolos sin uso | Sin errores. |
| OpenAPI, tipos y campos | Regeneración repetida sin cambios de hash. Incluye validación de reglas, captura anterior y datos difusos. |
| Migración de copia existente | 0005 aplicada; `alembic check` sin diferencias. |
| Docker desde volumen nuevo | Inicialización 0001→0005 correcta, semilla Mamdani cargada y servicios saludables. |
| Build Docker de API y frontend | Correcto con el código nuevo; no se reutilizó como prueba funcional la imagen antigua. |
| E2E sobre instalación existente | **3 aprobados**: flujo completo; captura ampliada/revisión/continuidad; sesión y responsive. |
| E2E sobre stack independiente desde cero | **3 aprobados**, 10,3 s. |
| Revisión de Resultado difuso | Sin errores de navegador; sin desbordamiento a 360, 768 y 1440 px. Capturas revisadas en escritorio/móvil. |

Las advertencias observadas fueron de depreciación de AnyIO/TestClient y de opciones de color de consola; no son fallos de aserciones. No se ejecutó el workflow remoto de GitHub.

## Correcciones comprobadas

- El método ya admite escritura carácter por carácter sin cerrar el panel ni truncarse a la primera letra.
- Se conserva el paso y la captura local al regresar o recargar; la recuperación del servidor indica que reemplaza la captura.
- Las observaciones anteriores se muestran con fecha y procedencia; solo los cambios se envían como observaciones nuevas.
- Las 28 variables ampliadas tienen captura en P6–P9; la revisión final es P10, con enlaces para editar.
- Los pendientes del Resultado permiten abrir la sección correspondiente.
- Las cuarentenas R36/R43/R46/R50/R51 abren un episodio persistente, conservan causas y no se levantan con una observación favorable posterior.
- La ampliación participa en requisitos, riesgo y plazos. El caso N13 deja de autorizar por omisión.
- NO_APLICA de vencimiento y ausencia documentada de estantes tiene tratamiento contextual.
- Las fechas de hechos iniciales se serializan correctamente al explicar una evaluación completa.
- La restricción SQL y el contrato admiten los diez pasos sin reescribir filas históricas.
- Los tres errores de Mypy del acceso local y el contrato desactualizado se corrigieron.
- Se retiraron 23 iconos sin consumidores, se separaron constructor/validación de reglas y gestión de captura, y se archivó el documento pegado fuera de `src`.
- Los colores de severidad se asignan por nombre, independientemente del orden de claves JSONB.
- La barra lateral se recoge al reducir la ventana a móvil y al navegar desde ella.
- Compose tiene nombre estable `poscosegran`, para no crear un proyecto distinto por el nombre de la carpeta y provocar conflictos de puertos.

## Demostración disponible

Se registró la unidad **«Demostración Mamdani — seguimiento térmico»** en el entorno local, con datos identificados como demostrativos:

| Caso | Resultado comprobado |
|---|---|
| Temperatura del almacén 10 °C y comprobaciones completas | Autorización con controles ordinarios. |
| Temperatura 24 °C, sin plan preventivo | Corregir y volver a evaluar para completar el seguimiento requerido. |
| Temperatura 24 °C, plan documentado cada cinco días | Autorización con seguimiento reforzado. |

En el último caso, el módulo de temperatura tiene pertenencias baja 0,2, media 0,8 y alta 0, centroide aproximado **44,819** y área **33,222**. Demuestra que el resultado difuso influye en la decisión antes del límite exacto de 25 °C.

Ruta local de ese resultado, tras iniciar sesión como productor:

`http://localhost:8080/resultado?id=9ba5e411-56f3-4904-b283-fe2d258a1a35`

Los datos originales no se borraron. Los E2E añaden registros con prefijo E2E al entorno local; la prueba de arranque desde cero utilizó un proyecto Docker independiente. Las pruebas Python operaron sobre copias de diagnóstico.

## Limpieza y documentación

Se configuraron `files.exclude` y `search.exclude` del editor para ocultar Markdown distintos de README, pruebas, logs y generados. Se conservaron documentación y pruebas en el control de versiones. El contexto/imagen Docker excluye pruebas y Markdown, pero incluye los YAML y casos de referencia necesarios para ejecutar el sistema.

Los planes iniciales permanecen como registro, ocultos en la vista cotidiana. `README.md` es la entrada visible y enlaza la explicación del modelo, sus curvas, su núcleo y este reporte.

## Cómo repetir

1. Seguir la preparación del README y arrancar Docker.
2. Ejecutar Ruff/Mypy y la suite Python con `POSCOSEGRAN_BD_URL_PRUEBAS` apuntando a una base de prueba migrada; definir `POSCOSEGRAN_EXIGIR_BD=1`.
3. Ejecutar por separado la prueba de privilegios con la cuenta restringida.
4. Regenerar OpenAPI/tipos y comprobar que la generación sea estable.
5. Ejecutar lint, TypeScript, build y `E2E_BASE_URL=http://localhost:8080` con Playwright.
6. Ejecutar `backend/.venv/Scripts/python.exe backend/scripts/comparar_modelos.py` para producir el detalle de diferencias en `test-results/comparacion_difusa.json`, excluido de Git.

La cuenta de pruebas de CI puede reactivar la semilla histórica durante sus fixtures; antes de usar la interfaz como demostración debe cargarse de nuevo la semilla vigente con `python -m poscosegran.conocimiento.cargar --activar`. El preparador Docker ya lo hace.

## Límites pendientes fuera de esta verificación técnica

- Validación de las curvas y políticas por especialistas del dominio y revisión de su aceptación académica.
- Supabase real, despliegue público y workflow remoto.
- Ensayos de campo, carga sostenida y validación de probabilidades: los índices no se presentan como probabilidades.

La explicación detallada de lo implementado, incluidas las diferencias respecto del diseño inicial, está en [CONVERSION_DIFUSA.md](CONVERSION_DIFUSA.md).
