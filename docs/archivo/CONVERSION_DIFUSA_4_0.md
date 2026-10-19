# Mamdani reducido para autorización de almacenamiento

## Versión vigente y alcance

Base **4.0**, parámetros **1.0**, motor **2.0.0-mamdani**. La semilla se encuentra en `knowledge/difuso/`. Determina condiciones para autorizar el almacenamiento de maíz chulpi; no evalúa despacho ni certifica consumo o inocuidad.

Un único núcleo combina **cuatro variables y nueve reglas lingüísticas**. En almacenamiento hermético la HR ambiental no participa: quedan tres entradas aplicables. Se conservan los 94 campos del catálogo como mediciones, verificaciones y trazabilidad, las 52 reglas documentales y sus 62 producciones exactas. No basta introducir cuatro números para obtener una autorización completa.

## Entradas y fundamento

| Entrada directa | Referencia r | Anchura w | Fuente y alcance |
|---|---:|---:|---|
| Humedad del grano | 13 % b.h. | 0,5 | R02/R03, S01/S03; requiere medición confirmada. >14 % conserva suspensión. |
| Temperatura del grano | 25 °C | 5 | R08, S01/S04; aplicar al grano la referencia ambiental es política preventiva documentada. Se exige lectura real del grano, sin sustituirla por temperatura ambiental. |
| Humedad relativa del almacén | 60 % HR | 10 | R07, S01/S05; únicamente no hermético. |
| Granos defectuosos | 7 % masa | 1 | R21, S09; referencia comercial heredada, pendiente de confirmar aplicabilidad y método para chulpi. No sumar otros defectos: pueden solaparse. |

Para dominio [L,U]: baja = [L,L,r−w,r], media = [r−w,r,r+w], alta = [r,r+w,U,U]. Dominios: humedad y defectos [0,100], temperatura [−30,90], HR [0,100]. Los nombres bajo/medio/alto describen severidad, no calidad.

Las referencias mantienen los fundamentos del catálogo. Las anchuras, las interacciones D07–D09, los consecuentes y los cortes son **POLITICA_PROTOTIPO**: no se atribuyen a las fuentes como curvas publicadas ni como calibración agronómica. Requieren validación de campo antes de uso operativo.

## Nueve reglas del núcleo

H = severidad de humedad, T = temperatura del grano, A = HR ambiental y D = granos defectuosos.

| Regla | Antecedente | Severidad de salida | Modalidad |
|---|---|---|---|
| D01 | H baja Y T baja Y A baja Y D baja | Baja | No hermético |
| D02 | H baja Y T baja Y D baja | Baja | Hermético |
| D03 | H media O T media O D media | Media | Ambas |
| D04 | A media | Media | No hermético |
| D05 | H alta O T alta O D alta | Alta | Ambas |
| D06 | A alta | Alta | No hermético |
| D07 | H media Y T media | Alta | Ambas |
| D08 | H media Y A media | Alta | No hermético |
| D09 | T media Y A media | Alta | No hermético |

Las reglas OR agrupan alternativas con el mismo consecuente; no se generan millones de filas. Las reglas de interacción hacen que dos condiciones medias puedan reforzar la severidad conjunta. Nueve reglas cubren las 81 combinaciones lingüísticas del modo no hermético y las 27 del hermético. Estas combinaciones no equivalen a otras tantas decisiones externas.

## Algoritmo y efecto real

1. Validar mediciones, confirmación de humedad y modalidad. Desconocido no es cero; NO_APLICA no inventa pertenencias.
2. Fuzzificar cada entrada aplicable.
3. Calcular activación de antecedentes con AND mínimo y OR máximo.
4. Recortar consecuentes con mínimo; agregar mediante envolvente máxima.
5. Integrar exactamente el área y el momento de la envolvente; centroide = momento/área.
6. Centroide <35: sin solicitud adicional. Desde 35: seguimiento reforzado. Desde 65: corrección preventiva. No se interpreta como probabilidad.
7. Resolver la autorización con restricciones exactas, evidencia necesaria, planes, plazos, fase e incidencias persistentes.

Consecuentes: baja [0,0,10,25], media [20,50,80], alta [70,85,100,100]. Una entrada aplicable ausente, inválida o fuera de dominio impide obtener la salida conjunta y produce pendientes. Se conservan las siete decisiones externas. Moho, contaminación, límites exactos, ingreso y cuarentena abierta mantienen su prioridad.

El núcleo no reemplaza una restricción mediante compensación: un centroide bajo no anula un hallazgo sanitario. La temperatura del almacén, la actividad de agua, el aumento térmico, el tiempo documentado, las separaciones, los otros defectos y las recomendaciones de aireación mantienen sus comprobaciones exactas. Se retiran únicamente sus antiguos módulos difusos independientes.

## Código para mostrar a la profesora

- `backend/src/poscosegran/sistema_difuso/motor.py`: lectura, fuzzificación, evaluación conjunta e integración en la decisión.
- `sistema_difuso/reglas.py`: antecedentes compuestos y activación mínimo/máximo.
- `sistema_difuso/pertenencia.py`: curvas triangulares/trapezoidales.
- `sistema_difuso/defuzzificacion.py`: envolvente e integración exacta por tramos.
- `sistema_difuso/validacion.py`: integridad del modelo y cobertura exhaustiva por modalidad.
- `knowledge/difuso/base_conocimiento.yaml`, sección `difuso`: cuatro variables, nueve reglas, salidas y política.
- `backend/scripts/generar_modelo_difuso.py`: generación reproducible de la semilla 4.0 desde la base documental original.

## Interfaz e historial

En P2 «Núcleo difuso» se muestran primero las entradas principales; después, la validación de las mediciones y los datos complementarios. La actividad de agua aparece cuando se declara medida; la aireación se ofrece en no hermético. «Mostrar todos los campos complementarios» permite revisar observaciones previas sin perderlas. No se rellenan automáticamente listas sanitarias como favorables.

En Resultado, el panel difuso aparece inmediatamente después de la decisión: muestra entradas, sus estados y pertenencias, una salida conjunta, centroide y antecedentes de las nueve reglas. En Conocimiento se distingue el núcleo D01–D09 de las reglas documentales R01–R52.

Las versiones 2.0 y 3.1 se conservan. `knowledge/historico_mamdani_3_1/` contiene la semilla anterior; las evaluaciones guardan su contenido inmutable en PostgreSQL y se reproducen con el algoritmo correspondiente. La activación de 4.0 afecta solo a evaluaciones nuevas. No se borra ningún dato ni se cambia el significado de un resultado histórico.

## Consecuencias y comprobación

Se reduce el núcleo de 20 evaluaciones independientes/60 reglas a una evaluación conjunta/9 reglas. Puede cambiar el seguimiento preventivo: las curvas independientes de distancias, tiempo o defectos secundarios dejan de generar solicitudes; sus límites exactos siguen activos. Las interacciones nuevas pueden reforzar correcciones preventivas. No se promete equivalencia numérica con 3.1.

El informe `docs/VERIFICACION_MAMDANI_REDUCIDO.md` registra las pruebas ejecutadas. Los 242 casos históricos conservan sus expectativas. `backend/scripts/comparar_modelos.py` genera comparación 2.0→4.0 en `test-results/comparacion_difusa.json`; la prueba de reproducción mantiene también 3.1. La comprobación de cobertura no constituye validación agronómica.
