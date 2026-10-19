# Conversión final a Mamdani para almacenamiento de maíz chulpi

## Alcance y cantidades reales

La base **5.0** y el motor **3.0.0-mamdani** deciden entre siete acciones de almacenamiento mediante inferencia Mamdani. Las 52 reglas documentales R01–R52 conservan la cobertura de condiciones sanitarias, operativas, plazos y recomendaciones. Sus producciones exactas preparan hechos verificables; ninguna ejecuta el selector final histórico R30 para una evaluación nueva.

| Nivel | Entradas | Reglas | Salida |
|---|---:|---:|---|
| Conservación | 4 mediciones: humedad del grano, temperatura del grano, HR del almacén y granos defectuosos | D01–D09: 9 | Severidad conjunta continua |
| Decisión | 11 antecedentes derivados o de contexto, incluida la severidad anterior | MF01–MF14: 14 | Una de 7 acciones tras el centroide |

En un recipiente hermético la HR ambiental no se utiliza: son tres mediciones aplicables en el primer nivel. Los 94 campos del catálogo incluyen además identidad, fechas, evidencia, higiene, recipiente, plagas y gestión; no son 94 entradas difusas simultáneas. Los indicadores categóricos observados tienen pertenencia 0/1, sin inventar intensidad intermedia. Fechas y validaciones siguen siendo exactas.

## Funciones y operaciones

Las cuatro curvas de cada magnitud siguen las referencias de R02/R07/R08/R21. Para una referencia `r`, anchura `w` y dominio `[L,U]`: baja `[L,L,r−w,r]`, media `[r−w,r,r+w]`, alta `[r,r+w,U,U]`. Referencias y anchuras: humedad 13 % b.h. y 0,5; temperatura 25 °C y 5; HR 60 % y 10; defectos 7 % masa y 1. En la salida intermedia: baja `[0,0,10,25]`, media `[20,50,80]`, alta `[70,85,100,100]`. D01–D02 describen conservación favorable por modalidad; D03–D06 detectan condiciones medias o altas; D07–D09 refuerzan la interacción entre dos condiciones medias.

La salida final codifica acciones, en este orden: autorización ordinaria `[0,0,6,12]`, autorización con monitoreo `[20,28,36]`, corregir y reevaluar `[44,52,60]`, evidencia pendiente `[66,70,74]`, bloquear ingreso `[78,81,84]`, retirar lote `[86,89,92]`, cuarentena `[95,98,100]`. Los cortes superiores de clasificación son 16, 40, 63, 76, 85, 93,5 y 101. Estas curvas y cortes son **POLITICA_PROTOTIPO**; no representan una escala física ni probabilidad de inocuidad. Las fuentes sustentan condiciones y límites documentales, no calibran estas funciones.

En ambos niveles: fuzzificación, AND=mínimo, OR=máximo, implicación=mínimo, agregación=máximo y centroide exacto de la envolvente por tramos. La clasificación lee el centroide final una sola vez. La validación del modelo comprueba referencias, cobertura de combinaciones lingüísticas, las siete salidas y la exclusión de decisiones permisivas cuando se presenta una condición crítica.

## Antecedentes y reglas finales

Las once entradas finales son `cuarentena`, `suspension`, `correccion`, `pendientes`, `evidencia`, `plan`, `monitoreo`, `condicional`, `fase`, `conservacion` y `baja_completa`. Las cuatro primeras agrupan solicitudes y hallazgos derivados de R01–R52; `evidencia` exige condiciones comunes, plazo y protección o rama condicional admisible. `plan` procede de un plan de seguimiento vigente; `fase` distingue ingreso, seguimiento o desconocida. `conservacion` es el centroide del primer nivel, con conjuntos bajo `[0,0,20,35]`, medio `[20,45,65]` y alto `[50,65,100,100]`. `baja_completa` señala pertenencia baja exactamente igual a uno para evitar autorización parcial sin plan. Desconocido no se interpreta como ausencia.

| Regla | Condición resumida | Salida |
|---|---|---|
| MF01 | Cuarentena o episodio abierto | Cuarentena |
| MF02–MF04 | Sin cuarentena; suspensión según fase | Bloquear, retirar o pendiente |
| MF05 | Sin las anteriores; corrección exigida | Corregir |
| MF06–MF07 | Sin las anteriores; pendientes o evidencia insuficiente | Pendiente |
| MF08–MF09 | Evidencia completa, plan, conservación baja; según monitoreo/condicional | Autorizar o autorizar con monitoreo |
| MF10–MF11 | Evidencia completa, plan, conservación media o alta | Monitorear o corregir |
| MF12–MF14 | Evidencia completa, sin plan; según conservación plenamente baja y seguimiento | Corregir o autorizar |

Cada regla incluye en el YAML sus negaciones y dependencias completas; la tabla solo resume. Si hay cuarentena, todas las reglas incompatibles tienen activación cero por sus propios antecedentes. Lo mismo se comprueba para suspensión, corrección y falta de evidencia. La cuarentena abierta se conserva como episodio hasta resolución técnica. La salida intermedia no emite por sí sola la autorización final. R10, R11 y R47 son recomendaciones; no se han convertido artificialmente en permisos sanitarios.

## Captura y responsabilidad de cada rol

La captura usa cuatro etapas: lote/modalidad, mediciones/plazo, verificaciones y resultado. El tercer paso muestra las comprobaciones del grano por unidad y permite reutilizar únicamente 13 campos de infraestructura e higiene de una inspección vigente del mismo almacén. Cada inspección incluye fecha, responsable, evidencia, revisión y vencimiento; una exposición a agua o cambio de revisión impide reutilizarla. Una observación actual o desconocida prevalece sobre una anterior. La vigencia máxima de siete días es política explícita del prototipo. Los campos omitidos no reciben respuestas favorables.

El productor registra sus unidades e inspecciones; el técnico accede a recursos asignados, evalúa y da seguimiento; el administrador administra asignaciones sin acceder a evaluaciones productivas; el ingeniero del conocimiento propone, simula y gestiona versiones del modelo. Los resultados anteriores se reproducen con su versión guardada.

## Código que contiene el algoritmo

- `backend/src/poscosegran/sistema_difuso/decision.py`: fuzzificación y activación de las 14 reglas finales, agregación, centroide y clasificación.
- `backend/src/poscosegran/sistema_difuso/motor.py`: ejecuta el nivel intermedio, llama a la inferencia final y guarda su traza.
- `backend/src/poscosegran/sistema_difuso/pertenencia.py`, `reglas.py`, `defuzzificacion.py`: curvas, operadores e integración exacta.
- `knowledge/difuso/base_conocimiento.yaml`, sección `difuso.decision`: definiciones declarativas que se versionan y pueden inspeccionarse.
- `backend/src/poscosegran/inferencia/`: hechos, cálculo documental, adquisición y explicación comunes. `sistema_experto/motor.py` conserva el resolutor R30 exclusivamente para versiones históricas.

El [plan de refactorización](../PLAN_REFACTORIZACION_SISTEMA_DIFUSO.md) contiene la matriz R01–R52 y los criterios de aceptación. El [informe de verificación final](VERIFICACION_MAMDANI_FINAL.md) registra pruebas, comparación y límites. La descripción de la base 4.0 se conserva en [el archivo histórico](archivo/CONVERSION_DIFUSA_4_0.md).
