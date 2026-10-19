# Verificación de la decisión final Mamdani — base 5.0

Fecha: 18 de octubre de 2026. Alcance: prototipo de autorización de almacenamiento de maíz chulpi. Los resultados de esta página se completan únicamente después de ejecutar cada comprobación; los informes de bases 3.1 y 4.0 permanecen como historial.

## Modelo inspeccionado

El YAML activo declara un nivel de conservación de cuatro mediciones y nueve reglas D01–D09, y un nivel de decisión de once antecedentes y catorce reglas MF01–MF14. En hermético se excluye la HR ambiental. La decisión final se toma a partir de agregación Mamdani y centroide de siete conjuntos de acciones. La tabla R30 no participa en evaluaciones nuevas. Las 52 reglas documentales mantienen hallazgos, límites exactos, cálculo de plazos y recomendaciones como hechos de entrada; las cifras 52 y 23 describen componentes distintos y no deben sumarse como si todos fueran reglas difusas.

El modelo rechaza reglas sin cobertura y casos en que una cuarentena, suspensión, corrección obligatoria o falta de evidencia active una conclusión permisiva. La prueba de aislamiento del selector histórico hace fallar deliberadamente la función R30 antigua mientras el motor 5.0 sigue entregando una decisión. En siete ensayos de condiciones críticas individuales, toda conclusión incompatible obtuvo activación cero. La cuarentena y la fase de suspensión se someten a casos distintos. El caso gradual documentado en las pruebas con plan y humedad 12,5/12,7/12,9 % produce centros finales distintos y pasa de monitoreo a corrección.

## Reproducción y criterios

Las pruebas incluyen aritmética de pertenencia, recorte, máximo y centroide; conservación de versiones 2.0, 3.1 y 4.0; casos de datos faltantes y `NO_APLICA`; aislamiento por almacén y lote; procedencia y caducidad de inspecciones; roles; y navegación de captura, resultado y seguimiento. Los 242 casos congelados de la base 2.0 se conservan sin reescribir expectativas. Las comparaciones entre 2.0, 3.1, 4.0 y 5.0 se generan en `test-results/` para revisar cambios de decisión, especialmente nuevas autorizaciones.

| Comparación de 242 casos | Decisiones distintas | Nuevas autorizaciones | Interpretación |
|---|---:|---:|---|
| Base 2.0 → 5.0 | 67 | 0 | 65 autorizaciones antiguas pasan a pendiente porque les falta evidencia exigida por la ampliación R31–R52; una pasa a corrección y una corrección a pendiente. |
| Base 3.1 → 5.0 | 8 | 0 | Corrección pasa a pendiente en ocho casos parciales. |
| Base 4.0 → 5.0 | 5 | 0 | Corrección pasa a pendiente en cinco casos parciales; entre ellos, fase desconocida no se interpreta como ingreso o seguimiento. |

La comparación congelada demuestra ausencia de autorizaciones nuevas en ese corpus, no equivalencia universal. Los ensayos completos prueban por separado las transiciones graduales con plan. Una salida pendiente requiere completar evidencia; no habilita almacenamiento.

La inspección del almacén reutiliza únicamente trece campos de infraestructura e higiene. La observación actual, incluso desconocida, tiene prioridad. La inspección vence por fecha, revisión o evento invalidante. La pantalla de administración puede asignar y revocar técnicos sin conceder acceso a evaluaciones productivas al administrador. Los resultados guardan la versión y la traza para reproducirlos.

## Resultados ejecutados

La suite Python completa contra PostgreSQL aprobó **253 pruebas, una omitida** en 15 min 22 s. La omitida comprueba privilegios con una credencial distinta y **aprobó por separado** con `poscosegran_app`. Después de iniciada la suite se añadieron cinco casos: tres intentos de autorizar desde reglas editadas incompatibles, dos hallazgos críticos simultáneos y un evento de agua que invalida solo a la unidad afectada; se ejecutaron y aprobaron en sus archivos focalizados. El archivo de decisión final aprobó **25** pruebas focalizadas en total.

Las **seis pruebas E2E** pasaron juntas en Docker (58,6 s): flujo, borrador, edición, responsive a 360/768/1440 px, explicación y roles. El administrador ve cero unidades en la lista productiva y pudo asignar un técnico; ese técnico registró la inspección compartida; el ingeniero consultó las catorce reglas finales. El inventario inicial muestra sus unidades antes de terminar todas las consultas de vigencia. La base principal llegó a migración `0006_mamdani_inspecciones`, conocimiento activo 5.0/motor 3.0.0-mamdani; `alembic check` informó que no hay operaciones pendientes. TypeScript, ESLint, Ruff y Mypy estricto (77 archivos fuente) aprobaron. El generador de OpenAPI, tipos y campos compartidos reprodujo los archivos existentes byte a byte.

Una segunda base PostgreSQL vacía recorrió `0001`→`0006`, activó la semilla 5.0 y pasó `alembic check`. Esto también comprueba la ruta de instalación limpia; la base principal comprobó la ruta de actualización sin perder volúmenes.

## Límite de validez

Las anchuras de las funciones, las reglas de interacción, las curvas de acciones y la vigencia máxima de siete días de inspección son **POLITICA_PROTOTIPO**. Son verificaciones de coherencia del software, no validación agronómica ni certificación de inocuidad. Los indicadores categóricos son 0/1; esto es compatible con Mamdani y evita simular grados que no fueron medidos. La autorización requiere evidencia suficiente y los límites documentales pertinentes.
