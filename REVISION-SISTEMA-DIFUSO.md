# Revisión del sistema experto difuso

Fecha: **2026-09-30**. Proyecto: POSCOSEGRAN-SI-DIFUSO. Referencia funcional: repositorio vecino POSCOSEGRAN-SI, consultado sin modificarlo.

## Dictamen técnico

El proyecto implementa un **sistema experto difuso Mamdani con resolución jerárquica de seguridad**. Conserva el objetivo original: orientar decisiones sobre almacenamiento poscosecha de maíz chulpi a partir de humedad, temperatura, ambiente, plagas, deterioro, infraestructura, trazabilidad e historial. El encadenamiento de hechos continúa siendo útil: ahora propaga grados de activación, en lugar de limitar las variables graduales a verdadero/falso.

La implementación es coherente con el enfoque Mamdani de las diapositivas después de las correcciones descritas en [changelog.md](changelog.md). Esto demuestra conformidad matemática y funcional del prototipo; no equivale a validación agrícola de sus políticas ni a certificación de inocuidad.

## Alcance y material contrastado

Se revisaron la base operativa, catálogo, especificación integrada, casos de referencia, motor, explicación, adquisición, API, modelos y migraciones, permisos SQL, autenticación, frontend, contratos generados, scripts, Docker y CI. Se contrastó el conocimiento con la base 2.0 del repositorio original y su documentación de objetivos.

Las siete presentaciones de `docs/` suman **200 páginas**. Las páginas citadas abajo se cuentan desde 1 dentro del PDF, no por el número que pudiera aparecer impreso en la lámina. Se extrajo su texto y se inspeccionaron visualmente las fórmulas clave.

| Material de la profesora | Páginas | Correspondencia con el proyecto |
|---|---:|---|
| [02 Conjuntos-Difusos.pdf](<docs/02 Conjuntos-Difusos.pdf>) | 36 | Universo, pertenencia en [0,1], diferencias entre conjuntos nítidos y difusos, interpretación lingüística. |
| [03 funciones de pertenenecia y operaciones con Conjuntos difusos.pdf](<docs/03 funciones de pertenenecia y operaciones con Conjuntos difusos.pdf>) | 30 | Γ y L lineales (p. 6), normalización, triangular y trapezoidal, complemento (p. 16), unión máximo e intersección mínimo (p. 18). |
| [04 medidas y relaciones borrosas.pdf](<docs/04 medidas y relaciones borrosas.pdf>) | 31 | Distancias de Hamming, Euclídea y Tchebychev (p. 11), borrosidad (p. 13), composición Max-Min (p. 26). |
| [06 razonamiento y reglas.pdf](<docs/06 razonamiento y reglas.pdf>) | 30 | Reglas lingüísticas, implicación Mamdani mínimo frente a alternativas (p. 18), Modus Ponens Generalizado y conjunto agregado frente a Sugeno (p. 25). |
| [07 Logica-Difusa.pdf](<docs/07 Logica-Difusa.pdf>) | 17 | Arquitectura de inferencia y paso de condiciones lingüísticas a decisiones. |
| [08- Logica-Difusa.pdf](<docs/08- Logica-Difusa.pdf>) | 29 | Cadena completa: singleton, AND mínimo, OR máximo, recorte Mamdani, agregación máximo (p. 14) y centroide discreto (p. 19). |
| [09 C-fuzzy.pdf](<docs/09 C-fuzzy.pdf>) | 27 | Particiones de Ruspini (p. 21) y Fuzzy C-Means con centros aprendidos (pp. 22–26), como alternativa de aprendizaje. |

Sugeno, Larsen y Fuzzy C-Means son técnicas alternativas presentadas en el curso. No es necesario mezclarlas con Mamdani para que este sistema de reglas sea difuso. No se implementó entrenamiento C-Means: las funciones se definen mediante conocimiento del dominio y no existe un conjunto de mediciones de campo para aprender centros. Las particiones de entrada sí satisfacen Σμ = 1.

## Correspondencia entre teoría y código

| Concepto | Implementación y comprobación |
|---|---|
| Variables lingüísticas | Diez entradas declaradas en `knowledge/base_conocimiento.yaml`; el motor no contiene sus umbrales como decisiones fijas. |
| Funciones de pertenencia | `sistema_experto/difuso.py`: Γ/L lineales, triangular, trapezoidal, S/Z, gaussiana y singleton. El modelo vigente usa particiones ancladas y cuatro términos de salida. |
| Normalización | Cada término debe alcanzar altura 1 **dentro de su universo**. Se corrigió la aceptación de picos situados fuera del intervalo. |
| Fuzzificación singleton | La lectura numérica produce pertenencias a sus etiquetas. No se confunde una medición desconocida con μ = 0. |
| AND / OR / NOT | `dominio/valores.py` y `sistema_experto/lenguaje.py`: mínimo, máximo y 1−μ. Hay pruebas de De Morgan, absorción, asociatividad e involución. |
| Activación y propagación | α = mínimo de antecedentes y aplicabilidad. Distintas causas del mismo hecho se combinan por máximo. La refracción evita duplicaciones y la inferencia termina en un punto fijo por etapas. |
| Implicación Mamdani | Salida de cada regla: μB′(y) = min(α, μB(y)). |
| Agregación | μsalida(y) = max de los consecuentes recortados. No se suman votos como probabilidades. |
| Defuzzificación | y* = Σy·μsalida(y) / Σμsalida(y), con 1001 puntos en [0,100]. Si el conjunto está vacío, el índice es `None`. |
| Borrosidad | Medida normalizada 2·media(min(μ,1−μ)) de las pertenencias evaluadas: 0 para valores nítidos, 1 para μ = 0,5. No representa probabilidad de error. |
| Distancia de Tchebychev | Máxima diferencia entre pertenencias para comparación de funciones; adquisición informa además la máxima variación del índice entre casos. Son comparaciones distintas. |
| Cortes α | R30 compara grados con los cortes declarados: gravedad plena, corrección/monitoreo/autorización según política. |
| Explicación | Guarda mediciones, μ, α, consecuentes, índice, rama, corte y origen de la decisión. La interfaz ahora los muestra. |
| Adquisición | Propuesta → validación → impacto → revisión independiente → activación, conservando versión y auditoría de evaluaciones anteriores. |

### Unión y etiqueta de intervalo: distinción corregida

A 24 °C, las pertenencias a TEMPLADA y CALIDA son 0,5. Su **unión de Zadeh** es max(0,5; 0,5) = 0,5. Un **intervalo compuesto TEMPLADA–CALIDA**, construido al quitar la frontera interna de una partición, vale 1 en ese punto. Son conjuntos diferentes.

Se separaron `grado_union` y `grado_compuesto`. El operador `alguno` continúa siendo OR máximo; `es: [TEMPLADA, CALIDA]` construye el intervalo compuesto empleado por las reglas originales. Esta compatibilidad mantiene la política de cubrir el intervalo completo, sin afirmar incorrectamente que una unión máximo elimina su valle. La sección 13.2 de la especificación incluye la sintaxis para ambas operaciones.

### Incertidumbre, no aplicabilidad y reglas nítidas

Un dato ausente se representa mediante [0,1] como ignorancia; un grado exacto 0,5 expresa pertenencia parcial. Ambos estados no son equivalentes. NO_APLICA tiene tratamiento separado y tampoco aporta una condición favorable.

Los booleanos observados, identidad de lote, fechas, barreras verificadas, plazos y límites comerciales permanecen nítidos. Un modelo difuso puede incorporar antecedentes con grados 0 y 1. No hay fundamento para inventar tolerancias sobre evidencia de moho, contaminación o una fecha vencida.

El operador auxiliar `implica` del lenguaje sirve para requisitos condicionales de aplicabilidad; no es el recorte de la salida Mamdani. En la inferencia SI–ENTONCES el recorte se realiza explícitamente con mínimo.

### Por qué el centroide no decide todo

Con consecuentes BAJA y CRITICA activados a 1, el centroide es aproximadamente 50. Ese promedio no puede cancelar una cuarentena. Por eso el sistema aplica primero R30 y sus prioridades, y permite al índice **endurecer**, nunca relajar, una decisión.

Esta resolución adicional es política del prototipo, no una fórmula universal de Mamdani. Las solicitudes graves parciales se degradan a corrección según su corte; no se presentan como una cuarentena plena. Los datos pendientes impiden autorización automática.

## Revisión de todas las reglas

La base conserva **52 identificadores principales**, **62 producciones operativas** y **9 ramas R30**. R30 es el resolutor compuesto, no una producción diagnóstica adicional. El contraste estructural con el original no encontró producciones eliminadas ni nuevos umbrales de dominio; se conservan los valores de los 29 parámetros originales, con parámetros adicionales para transiciones y cortes.

| Regla | Propósito y resultado de la revisión |
|---|---|
| R01 | Humedad NO_APTA: suspensión plena por fase; una activación parcial no concede almacenamiento normal. |
| R02 | Humedad CONDICIONAL: exige evaluación de admisibilidad, dictamen y plan; no autoriza sola. |
| R03 | Humedad APTA_BASE: condición favorable que debe combinarse con las demás comprobaciones. |
| R04 | Actividad de agua ALERTA: alerta hídrica/fúngica; requiere que la medición sea aplicable. |
| R05 | Medición de humedad no confirmada: corregir procedimiento; el número sin evidencia no autoriza. |
| R06 | Ambiente base: intervalo compuesto FRIA–TEMPLADA y HR seca, o hermeticidad verificada según modalidad. |
| R07 | HR adversa: rehúmedecimiento en almacenamiento no hermético; no atribuir HR exterior al interior sellado. |
| R08 | Temperatura adversa: intervalo compuesto CALIDA–MUY_CALIDA, corrección antes que autorización. |
| R09 | Aumento térmico: compara lecturas del mismo punto/método y ventana válida; revisar punto caliente. |
| R10 | Aireación favorable: solo con datos completos, equilibrio y exterior compatible; no inventa tabla faltante. |
| R11 | Aireación desfavorable: conserva impedimentos por humedad exterior, lluvia/niebla y relaciones adversas. |
| R12 | Protección hermética: exige barrera comprobada; no confundir envase hermético declarado con íntegro. |
| R13 | Hermeticidad comprometida: invalida protección y exige corrección; no coexiste con R12 en el mismo caso. |
| R14 | Infestación confirmada: cuarentena; el riesgo ambiental no sustituye esta evidencia. |
| R15 | Indicios de insectos: revisión de plagas; un descarte anterior solo sirve si cubre los indicios actuales. |
| R16 | Ambiente favorable a insectos: intervalo TEMPLADA–CALIDA en no hermético; monitoreo, no diagnóstico. |
| R17 | Indicios de roedores/aves: contaminación biológica sospechada y revisión/aislamiento según resolución. |
| R18 | Moho, olor, condensación o germinación: deterioro sospechado; transmite evidencia hacia R19. |
| R19 | Contaminación o deterioro: cuarentena prioritaria; ningún índice favorable elimina el veto. |
| R20 | Contaminación animal observada: encadena a cuarentena, conservando límites nítidos de cribado. |
| R21 | Defectos comerciales: no conformidad y corrección; límites transferidos no se vuelven tolerancias difusas. |
| R22 | Impurezas/quebrados: limpieza y clasificación; conserva fuente y límites comerciales. |
| R23 | Recipiente no apto: suspensión/corrección según fase; comprende grado alimentario y cierre. |
| R24 | Estiba no apta: corregir separaciones y reevaluar. |
| R25 | Almacén no higiénico: controles de limpieza y vigencia; no deducir cumplimiento de un dato ausente. |
| R26 | Aire contaminado o productos incompatibles: corregir; no diagnostica por sí sola afectación química del grano. |
| R27 | Controles vencidos: inspeccionar; un evento invalidante conserva su efecto hasta nuevo control. |
| R28 | Vida estimada próxima al límite: monitoreo y plazo compatible, con historial documentado. |
| R29 | Vida/plazo agotado: suspensión según fase; secar no reinicia vida consumida. |
| R30 | Única decisión final por prioridad, cortes α, pendientes, dictamen, plan e índice que solo endurece. |
| R31 | Filtración de agua: reparar e inspeccionar unidades expuestas; corrección. |
| R32 | Drenaje obstruido: despejar e inspeccionar; corrección. |
| R33 | Malla dañada/abertura: reparar barrera antiplagas; corrección. |
| R34 | Agua estancada/residuos exteriores: saneamiento del entorno; corrección. |
| R35 | Sacos usados/residuos de proceso: retirar y limpiar; corrección. |
| R36 | Agua en contacto con la unidad: cuarentena preventiva, no simple ajuste de humedad. |
| R37 | Paleta dañada/salientes: reparar e inspeccionar envase; corrección. |
| R38 | Estiba inestable/altura excesiva: reestibar; corrección. |
| R39 | Acceso de inspección obstruido/distancia insuficiente: liberar acceso; corrección. |
| R40 | Identificación ilegible: conciliar etiqueta, lote y registro; corrección. |
| R41 | Trazabilidad incompleta: completar registros; corrección. |
| R42 | Movimiento sin registro: reconstruir exposición e historial; corrección. |
| R43 | Contacto con unidad en cuarentena: aislamiento y cuarentena preventiva. |
| R44 | Cuarentena sin separación comprobada: corregir aislamiento; mantiene cuarentena abierta. |
| R45 | Derrame en piso: segregar grano y registrar cantidad; corrección. |
| R46 | Grano derramado reincorporado: cuarentena preventiva de unidad mezclada. |
| R47 | Rotación no justificada: aviso de despacho; no bloquea aptitud de almacenamiento. |
| R48 | Contacto con olores incompatibles: separar e inspeccionar; corrección. |
| R49 | Programa de plagas no documentado: completar gestión preventiva; corrección. |
| R50 | Plaguicida sin registro competente: cuarentena hasta revisión; no prescribe dosis. |
| R51 | Exposición química del grano: cuarentena y evaluación competente. |
| R52 | Vencimiento comercial aplicable superado: suspensión; independiente de vida estimada por la tabla. |

R31–R52 conservan sus antecedentes y acciones nítidos del original. Se añadieron pruebas de activación, decisión y no activación con evidencia favorable para R31–R51, y una prueba de fecha comercial vencida/vigente para R52.

| Rama de R30 | Función verificada |
|---|---|
| R30.1 | Cuarentena. |
| R30.2 | Bloquear ingreso por suspensión en INGRESO. |
| R30.3 | Retirar/suspender permanencia en SEGUIMIENTO. |
| R30.4 | Corregir y reevaluar. |
| R30.5 | Sin conclusión por datos exigibles pendientes. |
| R30.6 | Autorización condicional con dictamen y plan válido. |
| R30.7 | Autorización con monitoreo. |
| R30.8 | Autorización de almacenamiento en condiciones aptas. |
| R30.9 | Sin conclusión automática como cierre conservador. |

## Evidencia de verificación

- **Suite completa con PostgreSQL 16 real:** 593 pruebas pasaron; una comprobación de credencial restringida se omitió al usar la credencial administrativa y después pasó por separado con `poscosegran_app`.
- **Prueba añadida posteriormente para OR frente a intervalo compuesto:** pasó por separado. El conjunto final contiene 595 casos de prueba; se comprobaron todos usando la credencial que corresponde.
- **Regresión original:** los 242 casos congelados coinciden con la base 2.0 del repositorio vecino en decisión, rama, reglas, motivos y pendientes. La suite verifica también que δ = 0 reproduce esos 242 casos.
- **Lógica difusa:** funciones, Ruspini, normalización, centroides, desconocidos, límites efectivos, monotonía, conservadurismo y prohibición de autorizaciones con vetos.
- **Adquisición HTTP:** propuestas, impacto, roles, cuatro ojos, descarte, activación concurrente y auditoría sobre PostgreSQL.
- **Análisis estático:** Ruff y Mypy estricto sin errores (63 archivos de código Python); ESLint y TypeScript sin errores.
- **Build:** producción del frontend compilada correctamente.
- **Migraciones:** cinco revisiones aplicadas; `alembic check` sin operaciones pendientes.
- **Navegador:** tres pruebas Playwright pasaron contra API real; incluyen panel Mamdani, R18 a α = 1, salida CRITICA y navegación a 360, 768 y 1440 px.
- **Docker completo:** las mismas tres pruebas pasaron contra las imágenes construidas de web/API con PostgreSQL; servicios saludables e inicialización correcta. El preparador de despliegue conservó además la versión activa usando credenciales de migración y aplicación separadas.
- La dependencia Starlette/AnyIO emite una advertencia de deprecación en pruebas; no produjo fallos.

La base de pruebas fue un proyecto Compose aislado `poscosegran_revision_20260930`, puerto 55434 y volumen propio. No se usaron datos de usuarios reales ni se alteró el repositorio vecino.

### Reproducir

Crear primero un PostgreSQL de pruebas independiente y aplicar `backend/scripts/preparar_local.py` con las tres URL de administración, migraciones y aplicación configuradas. Para los controles Python:

```powershell
$env:POSCOSEGRAN_EXIGIR_BD = '1'
$env:POSCOSEGRAN_BD_URL_PRUEBAS = '<URL administrativa de la BD de pruebas>'
cd backend
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pytest -q -rs
.venv/Scripts/python.exe -m alembic check
```

Repetir la prueba `test_la_credencial_de_aplicacion_no_puede_crear_tablas` con la URL restringida. Desde la raíz ejecutar `pnpm lint`, `pnpm build` y `pnpm test:e2e` con API/frontend iniciados. La verificación de contrato compara artefactos regenerados con su versión en Git; antes de confirmar estos cambios, el diff del contrato actualizado es esperable.

## Límites y observaciones para defender el proyecto

1. Los anchos δ, cortes α y bandas del índice son políticas de diseño; requieren validación del experto y análisis con observaciones de campo.
2. Los límites de maíz amarillo duro, criterios comerciales y tabla NDSU se transfieren al prototipo; no se ha demostrado su ajuste a chulpi altoandino.
3. La tabla de tiempo no debe interpolarse ni extrapolarse. Una sustitución conservadora queda registrada; historial desconocido no se inicializa a cero.
4. Sin una tabla/lectura de humedad de equilibrio documentada, R10/R11 no deben presentar una recomendación automática de aireación.
5. Un índice 50 o una pertenencia 0,6 no significa 50 % o 60 % de probabilidad de contaminación.
6. Los casos de aceptación son regresiones de software, no ensayos de eficacia agrícola.
7. `backend/scripts/transcribir_base.py` sigue siendo una herramienta histórica incompatible con la semilla actual, ya advertida en `knowledge/README.md`. Se mantuvo sin ejecutar; el catálogo actual se conserva.
8. El despliegue público exige Supabase Auth y aprovisionar los roles de aplicación. El acceso local está expresamente bloqueado en producción.

## Ejemplos para la presentación

- **12,5 % de humedad y todas las condiciones conformes:** aptitud base plena; el resto de las comprobaciones sigue siendo necesario.
- **13,8 %:** CONDICIONAL = 0,4 y NO_APTA = 0,6; suspensión parcial se trata como corrección, no como autorización.
- **Moho visible:** evidencia nítida, cuarentena por R18 → R19 → R30.1 aunque otras condiciones sean favorables.
- **Dato de humedad desconocido:** pendiente; no simular humedad baja.
- **24 °C:** diferenciar OR máximo (0,5) de intervalo compuesto TEMPLADA–CALIDA (1).

El [plan de despliegue](PLAN-DESPLIEGUE.md) describe cómo presentar el repositorio mediante una URL pública con persistencia, autenticación y permisos.
