# Verificación de Mamdani reducido — base 4.0

Fecha local: 18 de octubre de 2026. Alcance: autorización de almacenamiento de maíz chulpi. Implementación aprobada en PLAN_REFACTORIZACION_SISTEMA_DIFUSO.md.

## Resultado ejecutado

| Comprobación | Resultado |
|---|---|
| Suite Python completa con PostgreSQL real | **227 aprobadas, 1 omitida por usar rol administrador**, 187,58 s. |
| Prueba omitida, ejecutada con poscosegran_app | **1 aprobada**: la credencial de aplicación no puede crear tablas. En conjunto, cubiertos los 228 casos. |
| Playwright contra Docker localhost:8080 | **5 aprobadas**, 16,4 s. |
| Mypy estricto desde backend/ | Sin errores, 68 archivos. |
| Ruff, ESLint, TypeScript con noUnusedLocals/noUnusedParameters | Aprobados. |
| Compilación de frontend y backend Docker | Imágenes construidas y servicios saludables. |
| Generación de semilla repetida | Hashes idénticos. |
| git diff --check | Aprobado; solo aviso de conversión CRLF del contrato previamente generado. |

Existe un aviso de deprecación de AnyIO en TestClient; no impidió las pruebas. La primera corrida utilizó por error una copia anterior a la migración 0005 y falló al insertar pendientes de los pasos 7–9. Se aplicó la migración a la copia aislada y se repitió la suite completa con el resultado de la tabla. La base principal ya tenía 0005. No se relajó ninguna restricción para hacer pasar una prueba.

La copia de pruebas es `poscosegran_refactor_4_20261018`, separada de la base principal y conservada. Las pruebas HTTP no usan SQLite ni sustituyen los servicios de persistencia. La suite usa el rol administrador para preparar conocimiento; la comprobación de permisos usa el rol real de aplicación.

## Matemáticas y cobertura

- Curvas triangulares y trapezoidales, hombros, límites y desconocidos.
- Centroide analítico y contraste con integración numérica independiente; agregación máxima de consecuentes recortados.
- Antecedentes AND mínimo y OR máximo; interacción D07 activa con humedad/temperatura medias.
- Cobertura completa de 81 combinaciones lingüísticas en no hermético y 27 en hermético, validada al cargar el modelo.
- Malla de 1.250 escenarios numéricos: cinco valores por entrada en cada modalidad, incluyendo transiciones intermedias.
- Ausencia de cualquiera de las cuatro mediciones impide obtener una salida favorable. HR ambiental queda explícitamente NO_APLICA en hermético, sin inventar pertenencias.
- Rechazo de reglas sin cobertura, referencias rotas, guardas incompatibles, identificadores duplicados y curvas inválidas.
- Moho, heces y exposición química conservan cuarentena aunque la severidad conjunta sea baja.
- Reproducción del motor histórico 0.8.0 y de la base Mamdani 3.1 con veinte módulos.

## API y UX

La API guarda y reproduce la traza con base 4.0/motor 2.0.0-mamdani. Se probaron adquisición/simulación de modelo, autorización ordinaria, necesidad de plan y autorización con seguimiento, además de las regresiones existentes de cuarentena y aislamiento.

Los cinco recorridos de navegador comprueban alta/borrador/cuarentena, persistencia de observaciones históricas y edición, navegación responsive, cuatro entradas principales, retorno desde revisión, conservación del método al escribir/recargar, nueve reglas en Conocimiento y gráficas del resultado conjunto. Sin errores JavaScript ni desbordamiento horizontal en 360, 768 y 1440 px. Se inspeccionó visualmente la captura y el panel de inferencia renderizados.

La prueba del centroide verifica 44.819 (o separador decimal equivalente) para temperatura del grano de 24 °C con las demás condiciones principales bajas. El valor coincide con el backend; no es un promedio de índices individuales.

## Impacto observado

Sobre los 242 casos históricos, sin alterar sus expectativas:

| Comparación | Cambios | Nuevas autorizaciones |
|---|---:|---:|
| Base 2.0 → 4.0 | 66 | 0 |
| Base 3.1 → 4.0 | 3 | 0 |

Los tres cambios frente a 3.1 son CORREGIR_Y_REEVALUAR → SIN_CONCLUSION_AUTOMATICA, en dirigido-32, dirigido-63 y suave-20. Retirar módulos preventivos independientes puede dejar como resolución principal la evidencia pendiente; el núcleo exige humedad confirmada y las otras entradas aplicables. No se autoriza por ausencia de datos.

Frente a 2.0: 34 autorizaciones ordinarias y 27 con monitoreo pasan a pendientes; dos ordinarias y tres con monitoreo pasan a corrección. Los casos congelados carecen de parte de la ampliación documental; la comparación no equivale a un ensayo de campo.

Comandos reproducibles: `backend/.venv/Scripts/python.exe backend/scripts/comparar_modelos.py` y el mismo comando con `--anterior 3.1`. Informes en `test-results/comparacion_difusa.json` y `test-results/comparacion_difusa_3_1_a_4_0.json`.

## Docker y demostración

Servicios principales saludables en http://localhost:8080; base activa **4.0**, motor **2.0.0-mamdani**. No se borraron volúmenes ni datos anteriores. Las pruebas añaden registros identificados como E2E/demostración en el entorno local.

Unidad: **Demostración 4 entradas — almacenamiento** (`c5bed1f7-273a-4b9c-9711-34574f35f60a`). Datos académicos, no mediciones de campo.

| Escenario | Resultado | Evaluación |
|---|---|---|
| Grano 10 °C, restantes condiciones completas | AUTORIZAR_ALMACENAMIENTO | 7a826079-f783-4c8d-a9aa-49373f22de39 |
| Grano 24 °C, sin plan | CORREGIR_Y_REEVALUAR | 61bbf3f9-da08-4985-8891-24c2f6692cbb |
| Grano 24 °C, plan de control cada cinco días | AUTORIZAR_CON_MONITOREO | 77e4c64d-cb5e-4648-a2d2-c7001541bee7 |

Último resultado: http://localhost:8080/resultado?id=77e4c64d-cb5e-4648-a2d2-c7001541bee7. También se consultó por API la explicación histórica 3.1 `9ba5e411-56f3-4904-b283-fe2d258a1a35`: HTTP 200, motor 1.0.0-mamdani y veinte módulos; el resultado nuevo devuelve motor 2.0.0-mamdani y un módulo conjunto.

## Límites

Las curvas, interacciones D07–D09 y cortes preventivos siguen siendo política del prototipo académico. La selección conserva las referencias originales; la aplicabilidad de los porcentajes comerciales al chulpi requiere confirmación. No se ejecutó validación agronómica de campo, certificación sanitaria, prueba de carga, despliegue público ni CI remoto. Se mantienen las verificaciones obligatorias: reducir entradas difusas no equivale a eliminar evidencia sanitaria.
