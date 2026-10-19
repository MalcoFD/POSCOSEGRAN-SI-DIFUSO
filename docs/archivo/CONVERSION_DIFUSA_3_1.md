> Archivo histórico: conversión modular 3.1, sustituida por la base 4.0.

# POSCOSEGRAN: conversión ejecutada a Mamdani

## Modelo vigente

La semilla vigente es `knowledge/difuso/base_conocimiento.yaml`, base **3.1**, parámetros 1.0 y motor **1.0.0-mamdani**. La base histórica 2.0 y sus 242 expectativas se conservan en la raíz de `knowledge/`.

El producto es un sistema experto difuso con restricciones explícitas. Evalúa condiciones de almacenamiento y conserva las siete decisiones, no certifica inocuidad ni autoriza por sí mismo venta o consumo.

Hay 94 campos de captura/contexto, 52 reglas documentales, 62 producciones de validación/restricción/encadenamiento y **20 módulos Mamdani con tres reglas lingüísticas cada uno: 60 producciones difusas**. No se afirma que las 52 reglas originales se hayan convertido una a una en 52 reglas difusas.

Los módulos utilizan entradas pertinentes y guardas contextuales. No se calcula el producto cartesiano de los 94 campos. Las variables booleanas mantienen presencia/ausencia comprobada: no se inventan grados de moho o exposición química que el formulario no mide.

## Dónde está el algoritmo para la exposición

1. `backend/src/poscosegran/sistema_difuso/pertenencia.py`: pertenencias triangulares y trapezoidales.
2. `sistema_difuso/defuzzificacion.py`: envolvente máxima e integración exacta por tramos de su centroide.
3. `sistema_difuso/motor.py`: evaluación de módulos, activaciones, agregación y efectos sobre solicitudes y control.
4. `sistema_difuso/validacion.py`: dominios, conjuntos, cobertura y referencias.
5. `dominio/motor.py`: selección de la implementación por contenido versionado.
6. `knowledge/difuso/base_conocimiento.yaml`, sección `difuso`: curvas, módulos y política como datos.

La agenda compartida calcula validaciones, hechos, tiempo y restricciones. El motor histórico no se ejecuta por separado para decidir una evaluación difusa. Sus comparaciones se reutilizan como límites conservadores: Mamdani añade seguimiento/corrección en zonas de transición, sin suavizar restricciones críticas. La implementación histórica se conserva para reproducir evaluaciones antiguas.

## Inferencia y significado

Por cada módulo aplicable con observación válida:

1. Calcular pertenencias a severidad baja, media y alta.
2. Activar las tres reglas `SI entrada es conjunto ENTONCES severidad es conjunto` con intensidad α igual a su pertenencia.
3. Recortar cada consecuente por mínimo con α.
4. Agregar los consecuentes por máximo.
5. Integrar la envolvente lineal y obtener `centroide = momento / área`.
6. Aplicar la política preventiva: centroide menor que 35 no añade solicitud; desde 35 pide monitoreo; desde 65 pide corrección. Los módulos de aireación son recomendaciones y no condiciones adicionales para autorizar.
7. Resolver las siete decisiones conservando prioridad, contexto, requisitos, planes y episodios.

Los cortes 35/65, los conjuntos de salida y las anchuras de transición son **POLITICA_PROTOTIPO**, no resultados publicados por FAO, SENASA o Codex. El índice de severidad 0–100 no es una probabilidad ni un porcentaje de inocuidad. Área cero o dato desconocido no equivale a condición favorable.

La salida difusa sí cambia el flujo: por ejemplo, temperatura del almacén de 24 °C puede solicitar seguimiento preventivo antes del límite exacto de 25 °C. Un plan requerido ausente pide corrección; el riesgo preventivo acorta el control. Una cuarentena nunca se compensa con una buena condición térmica.

## Variables y curvas numéricas

Para una referencia `r`, anchura `w` y dominio `[L,U]`, las curvas de severidad son:

- Baja: trapezoide `[L,L,r-w,r]`.
- Media: triángulo `[r-w,r,r+w]`.
- Alta: trapezoide `[r,r+w,U,U]`.
- En distancias y margen de secado se intercambian baja/alta: menos separación o menor margen representa mayor severidad.

| Módulo | Referencia r | Anchura w | Condición/origen |
|---|---:|---:|---|
| Humedad del grano | 13 % b.h. | 0,5 | R02; exige medición confirmada. El límite exacto >14 mantiene suspensión. |
| Temperatura del grano | 25 °C | 5 | R08; dato aplicable y procedencia conservada. |
| Temperatura del almacén | 25 °C | 5 | R08. |
| HR del almacén | 60 % | 10 | R07; solo no hermético. |
| Actividad de agua | 0,70 | 0,05 | R04; solo si fue medida. |
| Diferencia térmica | 2 °C | 1 | R09; lecturas comparables por método, punto y fecha. |
| Suciedad de origen animal | 0,1 % | 0,05 | R20; límites y cuarentena exactos conservados. |
| Granos defectuosos | 7 % | 1 | R21. |
| Granos enfermos | 0,5 % | 0,1 | R21. |
| Granos quebrados | 6 % | 1 | R22. |
| Materia orgánica extraña | 1,5 % | 0,3 | R22. |
| Materia inorgánica extraña | 0,5 % | 0,1 | R22. |
| Distancia al piso | 0,15 m | 0,05 | R24; severidad inversa. |
| Distancia a la pared | 0,50 m | 0,10 | R24; severidad inversa. |
| Distancia al techo | 1 m | 0,20 | R24; severidad inversa. |
| Distancia entre estantes | 1 m | 0,20 | R39; NO_APLICA con constancia de ausencia de estantes. |
| Vida consumida | 0,80 | 0,20 | R28; fracción del modelo, no probabilidad. |
| HR exterior | 70 % | 10 | R11; recomendación de aireación. |
| Humedad grano − equilibrio | 0 % b.h. | 0,5 | R10; severidad inversa, recomendación. |
| Temperatura exterior − grano | 0 °C | 2 | R11; recomendación. |

Consecuentes comunes de severidad: baja `[0,0,10,25]`, media `[20,50,80]`, alta `[70,85,100,100]`. Las guardas, dominios y fuentes completas se consultan en el YAML vigente y en el panel de conocimiento/adquisición.

Los puntos de referencia se toman de la base anterior con su naturaleza publicada, transferida, mixta o política. Las curvas no están calibradas con ensayos de chulpi. No se debe presentar esta conversión técnica como validación agronómica independiente.

## Cobertura, datos y persistencia

La sección `difuso.cobertura` identifica las 52 reglas de origen y distingue Mamdani con restricción de restricciones/contexto. Las nuevas observaciones exigibles de R31–R52 se incluyen en base 3.1; aislamiento y vencimiento se piden según contexto. R47 conserva su papel logístico.

Las observaciones ausentes no se inventan; NO_APLICA requiere contexto y motivo. El formulario muestra diez secciones y datos anteriores con fecha. Solo los campos modificados se envían como nuevas observaciones. Las evaluaciones antiguas no se editan ni se renombran como difusas.

Cada evaluación nueva guarda `_difuso` en su instantánea JSONB inmutable, junto con hechos iniciales, hash y versión. Se guardan pertenencias, reglas, α, área, centroide y curva de salida. No se necesita reescribir tablas históricas. La migración 0005 amplía únicamente la restricción de pasos a 1–10.

Las cuarentenas de R36/R43/R46/R50/R51 abren episodios persistentes con todas sus causas. Una observación posterior favorable no los cierra. La activación conserva una sola versión y separación de funciones; reactivar una base anterior afecta a evaluaciones futuras, no al historial ni a incidencias abiertas.

## Comparación con la base anterior

Se conservaron los 242 casos congelados y sus expectativas históricas. Frente a la base 3.1:

| Transición | Casos |
|---|---:|
| Autorización ordinaria → faltan datos | 34 |
| Autorización con seguimiento → faltan datos | 25 |
| Autorización ordinaria → corrección | 2 |
| Autorización con seguimiento → corrección | 5 |
| Sin conclusión → corrección | 1 |

Son 67 diferencias y **cero nuevas autorizaciones**. Las 59 transiciones a falta de datos corresponden a completar la ampliación R31–R52 antes ignorada. Las ocho transiciones a corrección incorporan la política preventiva/seguimiento del modelo. El detalle por caso se produce fuera del código fuente en `test-results/comparacion_difusa.json`; las expectativas no se regeneraron para hacer coincidir modelos distintos.

## Demostración reproducible

En Resultado, abrir «Cómo evaluó el sistema difuso», seleccionar una medición y mostrar valor, pertenencias, las tres activaciones, envolvente agregada, área y centroide. Después revisar la solicitud preventiva y la decisión general. Repetir con un caso con moho: las buenas mediciones no cancelan la cuarentena.

La prueba `tests/test_sistema_difuso.py` contrasta el centroide con valores analíticos e integración numérica independiente. Las pruebas API cubren traza, explicación, historial y adquisición. No se ha ejecutado validación de campo ni certificación sanitaria.
