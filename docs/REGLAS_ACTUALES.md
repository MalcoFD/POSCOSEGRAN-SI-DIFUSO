# Reglas actuales de POSCOSEGRAN

Este documento describe el conocimiento que ejecuta la base **6.0**, con parámetros **2.0** y motor **4.0.0-matricial**. Las matrices y funciones proceden de `knowledge/base_conocimiento.yaml`; `knowledge/catalogo.yaml` documenta esas mismas reglas y `knowledge/matriz_320.json` permite revisar su exportación completa.

## 1. Propósito y alcance

POSCOSEGRAN apoya la evaluación de condiciones de almacenamiento poscosecha de maíz chulpi. Produce un índice de intervención de 0 a 100 y una recomendación operativa. Un valor mayor representa mayor necesidad de intervención; no es un porcentaje de contaminación ni una probabilidad de inocuidad.

El modelo es Mamdani tipo 1 de un solo nivel. Publica dos matrices alternativas: **256 reglas no herméticas** y **64 herméticas**. Cada evaluación selecciona solo la matriz correspondiente a su modalidad; no ejecuta 320 reglas de ambas modalidades a la vez. La fase de ingreso o seguimiento identifica la evaluación y no cambia las reglas.

| Modalidad | Antecedentes de cada regla | Combinaciones |
|---|---|---:|
| No hermética | H, T, HR y S, cada una con cuatro etiquetas | 4×4×4×4 = 256 |
| Hermética | H, T y S, cada una con cuatro etiquetas | 4×4×4 = 64 |

H es humedad del grano; T, temperatura del grano; HR, humedad relativa del almacén; y S, estado físico y sanitario observado. H, T y HR son continuas. S es categórica, con pertenencias características 0/1. Esta diferencia forma parte explícita del modelo: no se afirma que las cuatro entradas sean continuas.

## 2. Entradas y funciones de pertenencia

Para una curva trapezoidal `[a,b,c,d]`, la pertenencia crece linealmente de 0 a 1 entre a y b, permanece en 1 entre b y c y disminuye linealmente de 1 a 0 entre c y d. Fuera del soporte vale 0. Cuando a=b o c=d se forma un hombro que incluye el extremo del dominio. Una curva triangular `[a,b,c]` es el caso con un único vértice de pertenencia 1 en b.

Los límites de dominio sirven para detectar mediciones incompatibles con la representación. No son intervalos recomendados de almacenamiento. Cada medición válida puede pertenecer parcialmente a dos etiquetas adyacentes; no se redondea primero a una sola categoría.

### Humedad del grano (% b.h.)

Campo: `humedad_grano`. Dominio admitido: 0 a 100 % b.h.

| Etiqueta | Vértices de la función |
|---|---|
| bajo | `[0, 0, 12, 12.5]` |
| medio | `[12, 12.5, 13, 13.5]` |
| alto | `[13, 13.5, 14, 14.5]` |
| muy_alto | `[14, 14.5, 100, 100]` |

Referencias 12–13 % de secado y 14 % de calidad transferidas de maíz amarillo duro. Vértices y etiquetas: diseño del prototipo.

### Temperatura del grano (°C)

Campo: `temperatura_grano`. Dominio admitido: -30 a 90 °C.

| Etiqueta | Vértices de la función |
|---|---|
| bajo | `[-30, -30, 15, 20]` |
| medio | `[15, 20, 20, 25]` |
| alto | `[20, 25, 25, 30]` |
| muy_alto | `[25, 30, 90, 90]` |

La referencia ambiental menor de 25 °C se adapta al grano. Transiciones 15–30 °C: diseño preventivo, no límite universal para chulpi.

### Humedad relativa del almacén (% HR)

Campo: `hr_almacen`. Dominio admitido: 0 a 100 % HR.

| Etiqueta | Vértices de la función |
|---|---|
| bajo | `[0, 0, 50, 55]` |
| medio | `[50, 55, 55, 60]` |
| alto | `[55, 60, 60, 70]` |
| muy_alto | `[60, 70, 100, 100]` |

Referencia ambiental menor de 60 % HR. Curvas 50–70 %: diseño. Excluida del modelo hermético.

### Estado físico y sanitario

Campo: `estado_fisico_sanitario`. El inspector ingresa directamente el estado más severo observado en una muestra representativa y documenta la evidencia, fecha y método. Para la categoría ingresada, μ=1; para las otras tres, μ=0. La aplicación no calcula esta categoría promediando una lista de comprobaciones.

| Código | Criterio de captura |
|---|---|
| `SIN_HALLAZGOS` | Inspección documentada sin daño físico relevante, indicios de plagas, moho visible ni insectos vivos. Ausencia de inspección no pertenece a este estado. |
| `DANO_FISICO` | Daño físico observado que requiere limpieza o clasificación, sin indicios biológicos ni hallazgo crítico. Describir muestra, tipo de defecto y proporción cuando se mida. |
| `INDICIOS_BIOLOGICOS` | Perforaciones anormales, polvillo o restos compatibles con plagas, sin insectos vivos ni moho observado. Es una sospecha, no un diagnóstico de infestación. |
| `HALLAZGO_CRITICO` | Moho visible o insectos vivos observados en el grano. Documentar el hallazgo; requiere separación y evaluación técnica. No cuantifica micotoxinas. |

Si concurren daño físico, indicios y moho visible o insectos vivos, se registra el hallazgo crítico. No disponer de inspección no equivale a `SIN_HALLAZGOS`. El moho observado no cuantifica micotoxinas; los indicios biológicos no confirman por sí solos una infestación.

### Aplicabilidad de la modalidad hermética

HR exterior no representa la humedad dentro de una barrera hermética íntegra y se excluye de esa matriz. No se rellena con cero ni con una estimación. Además de H, T y S se documentan los siguientes metadatos, que validan la aplicabilidad y no son nuevos antecedentes difusos:

| Campo | Valor admitido | Evidencia necesaria |
|---|---|---|
| `estado_barrera` | `INTEGRA` | Barrera y cierre íntegros, revisión documentada y vigente |
| `procedimiento_interno` | `SENSOR_INTERNO` o `INSPECCION_PREVIA_SELLADO` | Procedimiento que permite conocer condiciones internas y una inspección representativa del grano |

Ambos registros requieren fecha, método y evidencia vigente. Una lectura térmica interna aislada no demuestra ausencia de plagas o moho. Si la barrera perdió integridad, se debe revisar la modalidad y obtener las observaciones necesarias para evaluar como no hermético; el motor no convierte HR exterior en HR interna.

## 3. Salida e interpretación

Los consecuentes son conjuntos difusos sobre el índice de intervención. La decisión se obtiene después de agregar todas las reglas activadas y calcular un único centroide.

| Símbolo en matrices | Conjunto | Vértices | Intervalo del centroide | Código de decisión |
|---|---|---|---|---|
| F | favorable | `[0, 0, 6, 12]` | 0 ≤ z < 16 | `AUTORIZAR_ALMACENAMIENTO` |
| V | vigilancia | `[20, 28, 36]` | 16 ≤ z < 40 | `AUTORIZAR_CON_MONITOREO` |
| A | acondicionamiento | `[44, 52, 60]` | 40 ≤ z < 66 | `CORREGIR_Y_REEVALUAR` |
| S | suspension | `[73, 81, 89]` | 66 ≤ z < 93 | `SUSPENDER_ALMACENAMIENTO` |
| Q | separacion | `[95, 98, 100]` | 93 ≤ z ≤ 100 | `CUARENTENA` |

La clasificación usa límites superiores excluyentes: un centroide exactamente igual a 16, 40, 66 o 93 pertenece a la banda siguiente. El último límite técnico de la configuración es 101 para cubrir el dominio hasta 100.

| Recomendación | Actuación | Intervalo nominal de control |
|---|---|---|
| favorable | Condiciones favorables para conservar con controles ordinarios | 14 días |
| vigilancia | Conservar con vigilancia reforzada y registrar un plan de seguimiento | 7 días |
| acondicionamiento | Acondicionar el grano o corregir el ambiente y volver a evaluar | 3 días |
| suspension | Suspender el almacenamiento normal y solicitar revisión técnica | 1 días |
| separacion | Separar el lote y solicitar evaluación técnica por hallazgo sanitario | Sin autorización ordinaria; revisión técnica |

Los intervalos son una política del prototipo. La fecha del siguiente control se limita también por la caducidad de la observación aplicable más antigua; una recomendación favorable no concede automáticamente catorce días de autorización. Las autorizaciones solo corresponden a las dos primeras recomendaciones y pueden quedar invalidadas por incidencias o eventos del seguimiento.

## 4. Criterio de construcción de las reglas

El generador editorial `backend/scripts/generar_modelo_matricial.py` publica cada combinación con un consecuente explícito. Se emplea al construir o revisar el conocimiento; no se ejecuta como un segundo motor durante la evaluación.

Para explicar el diseño, las etiquetas numéricas tienen orden 0=bajo, 1=medio, 2=alto y 3=muy_alto. Los consecuentes se ordenan como 0=favorable, 1=vigilancia, 2=acondicionamiento, 3=suspensión y 4=separación.

1. Si S es hallazgo crítico, el consecuente es separación, independientemente de H, T y HR.
2. En los demás estados se parte del mayor nivel numérico observado en los antecedentes lingüísticos.
3. Si al menos dos antecedentes numéricos son altos o muy altos, se aumenta un nivel, con tope en suspensión.
4. Si la condición anterior no se cumple y al menos dos son medios o superiores, el resultado mínimo es acondicionamiento.
5. Daño físico impone al menos acondicionamiento; indicios biológicos imponen al menos suspensión. Sin hallazgos no añade un mínimo sanitario.

Para construir la matriz hermética se consideran solo H y T en estas interacciones. La implementación del generador utiliza un valor ordinal neutro para el eje omitido; ese recurso editorial no representa una medición de HR ni se incorpora a la evaluación.

Las matrices siguientes son la definición completa de las reglas publicadas. Cada celda contiene `identificador → consecuente`. Las etiquetas fijadas en el título, la fila y la columna determinan todos sus antecedentes. No son reglas adicionales a las del YAML.

## 5. Matrices no herméticas: NH001–NH256

Cada tabla fija H y S. Las filas representan T y las columnas HR. Por ejemplo, en una tabla con H=bajo y S=sin hallazgos, la celda T=bajo, HR=bajo expresa: **SI H es bajo Y T es bajo Y HR es bajo Y S es sin hallazgos, ENTONCES favorable** (`NH001`).

Los índices ordinales h, t, r y s van de 0 a 3 en el orden declarado. El número de regla es `1 + 64h + 16t + 4r + s`; así se puede localizar una combinación sin cambiar su significado.

### H=Bajo; S=SIN_HALLAZGOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH001` → F | `NH005` → V | `NH009` → A | `NH013` → S |
| Medio | `NH017` → V | `NH021` → A | `NH025` → A | `NH029` → S |
| Alto | `NH033` → A | `NH037` → A | `NH041` → S | `NH045` → S |
| Muy alto | `NH049` → S | `NH053` → S | `NH057` → S | `NH061` → S |

### H=Bajo; S=DANO_FISICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH002` → A | `NH006` → A | `NH010` → A | `NH014` → S |
| Medio | `NH018` → A | `NH022` → A | `NH026` → A | `NH030` → S |
| Alto | `NH034` → A | `NH038` → A | `NH042` → S | `NH046` → S |
| Muy alto | `NH050` → S | `NH054` → S | `NH058` → S | `NH062` → S |

### H=Bajo; S=INDICIOS_BIOLOGICOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH003` → S | `NH007` → S | `NH011` → S | `NH015` → S |
| Medio | `NH019` → S | `NH023` → S | `NH027` → S | `NH031` → S |
| Alto | `NH035` → S | `NH039` → S | `NH043` → S | `NH047` → S |
| Muy alto | `NH051` → S | `NH055` → S | `NH059` → S | `NH063` → S |

### H=Bajo; S=HALLAZGO_CRITICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH004` → Q | `NH008` → Q | `NH012` → Q | `NH016` → Q |
| Medio | `NH020` → Q | `NH024` → Q | `NH028` → Q | `NH032` → Q |
| Alto | `NH036` → Q | `NH040` → Q | `NH044` → Q | `NH048` → Q |
| Muy alto | `NH052` → Q | `NH056` → Q | `NH060` → Q | `NH064` → Q |

### H=Medio; S=SIN_HALLAZGOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH065` → V | `NH069` → A | `NH073` → A | `NH077` → S |
| Medio | `NH081` → A | `NH085` → A | `NH089` → A | `NH093` → S |
| Alto | `NH097` → A | `NH101` → A | `NH105` → S | `NH109` → S |
| Muy alto | `NH113` → S | `NH117` → S | `NH121` → S | `NH125` → S |

### H=Medio; S=DANO_FISICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH066` → A | `NH070` → A | `NH074` → A | `NH078` → S |
| Medio | `NH082` → A | `NH086` → A | `NH090` → A | `NH094` → S |
| Alto | `NH098` → A | `NH102` → A | `NH106` → S | `NH110` → S |
| Muy alto | `NH114` → S | `NH118` → S | `NH122` → S | `NH126` → S |

### H=Medio; S=INDICIOS_BIOLOGICOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH067` → S | `NH071` → S | `NH075` → S | `NH079` → S |
| Medio | `NH083` → S | `NH087` → S | `NH091` → S | `NH095` → S |
| Alto | `NH099` → S | `NH103` → S | `NH107` → S | `NH111` → S |
| Muy alto | `NH115` → S | `NH119` → S | `NH123` → S | `NH127` → S |

### H=Medio; S=HALLAZGO_CRITICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH068` → Q | `NH072` → Q | `NH076` → Q | `NH080` → Q |
| Medio | `NH084` → Q | `NH088` → Q | `NH092` → Q | `NH096` → Q |
| Alto | `NH100` → Q | `NH104` → Q | `NH108` → Q | `NH112` → Q |
| Muy alto | `NH116` → Q | `NH120` → Q | `NH124` → Q | `NH128` → Q |

### H=Alto; S=SIN_HALLAZGOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH129` → A | `NH133` → A | `NH137` → S | `NH141` → S |
| Medio | `NH145` → A | `NH149` → A | `NH153` → S | `NH157` → S |
| Alto | `NH161` → S | `NH165` → S | `NH169` → S | `NH173` → S |
| Muy alto | `NH177` → S | `NH181` → S | `NH185` → S | `NH189` → S |

### H=Alto; S=DANO_FISICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH130` → A | `NH134` → A | `NH138` → S | `NH142` → S |
| Medio | `NH146` → A | `NH150` → A | `NH154` → S | `NH158` → S |
| Alto | `NH162` → S | `NH166` → S | `NH170` → S | `NH174` → S |
| Muy alto | `NH178` → S | `NH182` → S | `NH186` → S | `NH190` → S |

### H=Alto; S=INDICIOS_BIOLOGICOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH131` → S | `NH135` → S | `NH139` → S | `NH143` → S |
| Medio | `NH147` → S | `NH151` → S | `NH155` → S | `NH159` → S |
| Alto | `NH163` → S | `NH167` → S | `NH171` → S | `NH175` → S |
| Muy alto | `NH179` → S | `NH183` → S | `NH187` → S | `NH191` → S |

### H=Alto; S=HALLAZGO_CRITICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH132` → Q | `NH136` → Q | `NH140` → Q | `NH144` → Q |
| Medio | `NH148` → Q | `NH152` → Q | `NH156` → Q | `NH160` → Q |
| Alto | `NH164` → Q | `NH168` → Q | `NH172` → Q | `NH176` → Q |
| Muy alto | `NH180` → Q | `NH184` → Q | `NH188` → Q | `NH192` → Q |

### H=Muy alto; S=SIN_HALLAZGOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH193` → S | `NH197` → S | `NH201` → S | `NH205` → S |
| Medio | `NH209` → S | `NH213` → S | `NH217` → S | `NH221` → S |
| Alto | `NH225` → S | `NH229` → S | `NH233` → S | `NH237` → S |
| Muy alto | `NH241` → S | `NH245` → S | `NH249` → S | `NH253` → S |

### H=Muy alto; S=DANO_FISICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH194` → S | `NH198` → S | `NH202` → S | `NH206` → S |
| Medio | `NH210` → S | `NH214` → S | `NH218` → S | `NH222` → S |
| Alto | `NH226` → S | `NH230` → S | `NH234` → S | `NH238` → S |
| Muy alto | `NH242` → S | `NH246` → S | `NH250` → S | `NH254` → S |

### H=Muy alto; S=INDICIOS_BIOLOGICOS

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH195` → S | `NH199` → S | `NH203` → S | `NH207` → S |
| Medio | `NH211` → S | `NH215` → S | `NH219` → S | `NH223` → S |
| Alto | `NH227` → S | `NH231` → S | `NH235` → S | `NH239` → S |
| Muy alto | `NH243` → S | `NH247` → S | `NH251` → S | `NH255` → S |

### H=Muy alto; S=HALLAZGO_CRITICO

| T \ HR | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `NH196` → Q | `NH200` → Q | `NH204` → Q | `NH208` → Q |
| Medio | `NH212` → Q | `NH216` → Q | `NH220` → Q | `NH224` → Q |
| Alto | `NH228` → Q | `NH232` → Q | `NH236` → Q | `NH240` → Q |
| Muy alto | `NH244` → Q | `NH248` → Q | `NH252` → Q | `NH256` → Q |

## 6. Matrices herméticas: H001–H064

Cada tabla fija S. Las filas representan H y las columnas T. HR no interviene. Por ejemplo, `H001` expresa: **SI H es bajo Y T es bajo Y S es sin hallazgos, ENTONCES favorable**.

El número de regla es `1 + 16h + 4t + s`, con índices de 0 a 3 en el mismo orden de etiquetas.

### S=SIN_HALLAZGOS

| H \ T | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `H001` → F | `H005` → V | `H009` → A | `H013` → S |
| Medio | `H017` → V | `H021` → A | `H025` → A | `H029` → S |
| Alto | `H033` → A | `H037` → A | `H041` → S | `H045` → S |
| Muy alto | `H049` → S | `H053` → S | `H057` → S | `H061` → S |

### S=DANO_FISICO

| H \ T | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `H002` → A | `H006` → A | `H010` → A | `H014` → S |
| Medio | `H018` → A | `H022` → A | `H026` → A | `H030` → S |
| Alto | `H034` → A | `H038` → A | `H042` → S | `H046` → S |
| Muy alto | `H050` → S | `H054` → S | `H058` → S | `H062` → S |

### S=INDICIOS_BIOLOGICOS

| H \ T | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `H003` → S | `H007` → S | `H011` → S | `H015` → S |
| Medio | `H019` → S | `H023` → S | `H027` → S | `H031` → S |
| Alto | `H035` → S | `H039` → S | `H043` → S | `H047` → S |
| Muy alto | `H051` → S | `H055` → S | `H059` → S | `H063` → S |

### S=HALLAZGO_CRITICO

| H \ T | Bajo | Medio | Alto | Muy alto |
|---|---|---|---|---|
| Bajo | `H004` → Q | `H008` → Q | `H012` → Q | `H016` → Q |
| Medio | `H020` → Q | `H024` → Q | `H028` → Q | `H032` → Q |
| Alto | `H036` → Q | `H040` → Q | `H044` → Q | `H048` → Q |
| Muy alto | `H052` → Q | `H056` → Q | `H060` → Q | `H064` → Q |

### Recuento de consecuentes

| Consecuente | No hermético | Hermético | Total |
|---|---:|---:|---:|
| favorable | 1 | 1 | 2 |
| vigilancia | 3 | 2 | 5 |
| acondicionamiento | 36 | 13 | 49 |
| suspension | 152 | 32 | 184 |
| separacion | 64 | 16 | 80 |

Las 80 reglas de separación corresponden exactamente al estado crítico: 64 no herméticas y 16 herméticas. Los antecedentes numéricos favorables no pueden compensar moho visible o insectos vivos observados. La matriz conserva el orden de gravedad en sus 912 comparaciones entre etiquetas vecinas; esta propiedad lingüística no garantiza por sí sola monotonía del centroide en todo punto continuo.

## 7. Cálculo de una evaluación

1. **Recuperar la instantánea.** El servidor resuelve las observaciones aplicables y sus revisiones, conserva la procedencia y selecciona la versión publicada de conocimiento.
2. **Validar la captura.** Comprueba valor, unidad, dominio, método, fecha, evidencia sanitaria y aplicabilidad hermética. La humedad exige método `INSTRUMENTAL` o `LABORATORIO`. Una fecha futura o una antigüedad mayor de 168 horas impide emitir un índice.
3. **Fuzzificar.** Para cada medición válida calcula todos sus grados de pertenencia. Para S construye el vector característico 0/1.
4. **Seleccionar la matriz.** Se usa NH o H según la modalidad, sin mezclar ambas.
5. **Activar cada regla.** `α_r = min(μ_1, μ_2, …, μ_n)`, donde n es cuatro para NH y tres para H. Solo las reglas con α positivo contribuyen a la salida.
6. **Aplicar la implicación.** El consecuente se recorta: `μ_r(z) = min(α_r, μ_consecuente(z))`.
7. **Agregar.** Se forma `μ_agregada(z) = max_r μ_r(z)`. Si varias reglas comparten un consecuente, basta recortarlo a la mayor α de ese grupo; no se suman sus áreas.
8. **Defuzzificar.** `z* = ∫ z·μ_agregada(z) dz / ∫ μ_agregada(z) dz`. El motor integra exactamente los segmentos de la envolvente lineal por tramos, incluidos sus cruces. No promedia centroides individuales ni obtiene el resultado desde el gráfico muestreado.
9. **Interpretar y persistir.** Clasifica el centroide, fija las actuaciones y guarda instantánea, versión, grados, activaciones, curva, área y resultado. La respuesta permite reconstruir la explicación.

Si falta una observación necesaria, el dato es desconocido o no satisface la validación, se devuelve `SIN_CONCLUSION_AUTOMATICA` y se indican los pendientes. No se emite índice, no se activan reglas y no se sustituye el dato por cero. Este estado no constituye una sexta etiqueta de salida.

## 8. Cuatro ejemplos reproducibles

Son escenarios simulados, con fechas vigentes, método adecuado y evidencia completa. Sus datos y trazas se conservan en `knowledge/corridas_4.json`. En hermético también deben completarse los metadatos indicados en la sección 2.

| Ejemplo | Modalidad y entradas | Reglas activadas | Área | Primer momento | Centroide | Recomendación |
|---|---|---|---:|---:|---:|---|
| M320-L01 | Hermético; H=12 %, T=10 °C, S=sin hallazgos | H001: α=1 | 9 | 42 | 4,666667 | Autorizar almacenamiento |
| M320-L02 | No hermético; H=12 %, T=18 °C, HR=50 %, S=sin hallazgos | NH001: α=0,4; NH017: α=0,6 | 11,04 | 211,584 | 19,165217 | Autorizar con monitoreo |
| M320-L03 | No hermético; H=13,5 %, T=25 °C, HR=60 %, S=sin hallazgos | NH169: α=1 | 8 | 648 | 81 | Suspender almacenamiento |
| M320-L04 | No hermético; H=12 %, T=10 °C, HR=50 %, S=hallazgo crítico | NH004: α=1 | 2,5 | 244,166667 | 97,666667 | Separar y solicitar revisión técnica |

En M320-L02, T=18 activa bajo con `(20−18)/(20−15)=0,4` y medio con `(18−15)/(20−15)=0,6`. Los otros antecedentes tienen pertenencia 1, por lo que esas son las dos activaciones mínimas. La unión máxima de sus consecuentes recortados produce área 11,04 y momento 211,584; el cociente es 19,165217. No es el promedio simple de las dos recomendaciones.

## 9. Historial, seguimiento y versiones

La recomendación numérica y su interpretación pertenecen a la evaluación guardada. Una incidencia abierta, una observación caducada o un evento posterior puede impedir utilizar una autorización sin modificar el centroide histórico. Un hallazgo crítico abre el seguimiento correspondiente; cambiar posteriormente la categoría capturada no cierra por sí solo una incidencia existente. Se requiere resolución técnica y una nueva evaluación cuando proceda.

Los controles de permisos, fechas, integridad de barrera, idempotencia y vigencia no constituyen otra matriz de recomendaciones. La aplicación conserva esas funciones para que una recomendación pueda utilizarse y auditarse correctamente. No se ejecutan las producciones del motor sustituido, ni cálculos de vida útil o de actividad de agua estimada.

Las propuestas de conocimiento se validan antes de publicarse: cobertura completa, ausencia de combinaciones duplicadas, identificadores únicos, operadores, salidas, protocolo sanitario y orden lingüístico. Las evaluaciones conservan la versión con que fueron emitidas. Una versión histórica de otro modelo puede consultarse mediante sus resultados guardados; el motor matricial no la recalcula.

## 10. Fundamento y límites

Las referencias poscosecha orientan la selección de variables y las precauciones. SENASA aporta referencias de secado de 12–13 %, humedad de calidad de hasta 14 % y condiciones ambientales de almacenamiento; su transferencia desde maíz amarillo duro al chulpi requiere validación. Las precauciones sobre moho, segregación y almacenamiento hermético se apoyan en las referencias de Codex, FAO y Purdue.

Los vértices, las interacciones entre antecedentes, los cinco cortes de interpretación, la ventana de siete días y los intervalos de control son **políticas del prototipo**. Las fuentes no publican ni validan esta matriz de 320 reglas. El sistema no certifica inocuidad, no estima micotoxinas y no determina una duración segura universal.

La auditoría de superficie examinó 119.808 puntos y 344.000 comparaciones vecinas. No encontró descensos de categoría en esa malla; sí oscilaciones locales del índice, con descensos máximos de 1,099292 puntos en no hermético y 0,790909 en hermético. Es un diagnóstico finito, no una demostración de monotonía continua global ni una validación agronómica. El procedimiento puede reproducirse con `backend/scripts/auditar_superficie.py`.

### Referencias del catálogo

- **S01**: Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).

- **S02**: Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).

- **S03**: Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).

- **S04**: Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).

- **S05**: Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).

- **S06**: Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).

- **S07**: Hellevang, K., & Proulx, R. (2026, 27 de febrero). *Proper grain storage crucial in late winter and spring*. North Dakota State University Extension. [Artículo](https://www.ag.ndsu.edu/news/newsreleases/2026/february/proper-grain-storage-crucial-in-late-winter-and-spring).

- **S08**: North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).

- **S09**: Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.
