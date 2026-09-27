# POSCOSEGRAN: informe de impacto de la migración a inferencia difusa

**Versiones:** base nítida 2.0 / parámetros 1.0 / motor 0.8.0 → base difusa 3.1 / parámetros 2.0 / motor 1.0.0.
**Fecha:** 27 de septiembre de 2026.
**Alcance:** comparar decisiones de ambas bases sobre los 242 casos de referencia y sobre una malla alrededor de cada umbral. Las fórmulas y definiciones están en la sección 13 de `POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md`.

## 1. Resumen

La migración cumple las tres propiedades que se exigieron antes de aprobarla.

1. **Extensión conservadora.** Con todos los anchos de transición a 0, la base difusa reproduce los 242 casos de la versión 2.0 sin una sola diferencia en decisión, rama, reglas activadas, motivos ni datos pendientes. Los casos de aceptación C01–C40 pasan sin tocar una expectativa. La lógica nítida es, por tanto, un caso particular del modelo.
2. **Nunca más permisiva.** En 9 661 evaluaciones sobre una malla que recorre cada ancla (humedad, temperatura, HR y actividad de agua), ninguna decisión difusa es menos severa que la nítida. Hay 8 611 iguales y 1 050 más severas.
3. **Impacto acotado y explicable.** Con los anchos aprobados, 14 de los 242 casos cambian de decisión y 3 más cambian solo en las reglas activadas. Todos los cambios van hacia más severidad y se explican por la proximidad a un umbral publicado.

## 2. Método

- **Casos:** `casos_referencia_nitida.json`, que congela lo decidido por la base 2.0 (40 de aceptación y 202 variaciones estratificadas por decisión).
- **Comparación:** cada caso se evalúa con la base 3.1 y se compara con lo congelado. El resultado queda en `casos_referencia.json`, que conserva los mismos casos e incluye el índice de severidad.
- **Malla:** para cada caso se sustituye una lectura por valores situados en el ancla, en el centro de la rampa y a ambos lados:
  - humedad: 14 valores entre 12,4 % y 14,1 %;
  - temperatura del grano: 15 valores alrededor de 15, 25 y 35 °C;
  - temperatura del almacén: 5 valores;
  - HR del almacén: 5 valores;
  - actividad de agua: 5 valores.

  Se compara la severidad de la decisión nítida con la difusa, según el orden autorizar < autorizar con monitoreo < sin conclusión < corregir < bloquear/retirar < cuarentena.
- **Reproducción:** `backend/tests/test_aceptacion_difusa.py` ejecuta una versión reducida de la malla para δ × 0,5, × 1 y × 2 en cada integración continua.

## 3. Casos que cambian

| Caso | Lectura relevante | Nítida 2.0 | Difusa 3.1 | Índice | Causa |
|---|---|---|---|---|---|
| C02 | humedad 13,0 % | Autorizar (R30.8) | Corregir (R30.4) | 38,9 | 13,0 es núcleo de CONDICIONAL; sin dictamen la banda no es admisible |
| C04 | humedad 14,0 %, dictamen y plan | Autorizar con monitoreo (R30.6) | Bloquear ingreso (R30.2) | 50,0 | el núcleo de NO_APTA empieza en el ancla de 14 % |
| dirigido-3, 14, 41 | humedad 14,0 % | Corregir (R30.4) | Bloquear ingreso (R30.2) | 50,0 | ídem |
| dirigido-20, 24, 75, 89 | grano a 24 °C, plan | Autorizar con monitoreo (R30.7) | Corregir (R30.4) | 35,0 | riesgo térmico 0,5, que alcanza el 0,5-corte de corrección |
| dirigido-48, 109, 139 | grano a 14 °C, plan | Autorizar (R30.8) | Autorizar con monitoreo (R30.7) | 21,2 | ambiente favorable a insectos 0,5: monitoreo |
| dirigido-90, 101 | grano a 14 °C, sin plan | Autorizar (R30.8) | Corregir (R30.4) | 35,0 | monitoreo 0,5 sin plan vigente: corrección (sección 5) |
| suave-69 | vida consumida próxima al límite | Cuarentena | Cuarentena | 50,7 | además, R29 se activa parcialmente |
| suave-139, 148 | aire exterior en transición | Cuarentena | Cuarentena | 50,0 | además, R11 se activa parcialmente |

Distribución de decisiones sobre los 242 casos:

| Decisión | Nítida 2.0 | Difusa 3.1 |
|---|---|---|
| Autorizar | 36 | 30 |
| Autorizar con monitoreo | 30 | 28 |
| Sin conclusión automática | 30 | 30 |
| Corregir y reevaluar | 45 | 49 |
| Bloquear ingreso | 32 | 36 |
| Retirar lote | 29 | 29 |
| Cuarentena | 40 | 40 |

## 4. Sensibilidad a los anchos de transición

| Factor sobre los δ aprobados | Casos idénticos a la base 2.0 | Menos severos que la nítida |
|---|---|---|
| 0 | 242/242 | 0 |
| 0,5 | 231/242 | 0 |
| 1 (aprobado) | 225/242 | 0 |
| 2 | 45/242 | 0 |

El salto con δ × 2 no es una anomalía del modelo. El caso base de referencia tiene 12,5 % de humedad, que con δ_humedad = 0,5 es justo el borde de la rampa. Con δ_humedad = 1, 12,5 % pasa a ser "mitad condicional" y casi todos los casos derivados del caso base cambian.

**Conclusión:** δ_humedad es el parámetro más sensible del modelo y el primero que debe validarse con datos de campo y con el experto. Los demás anchos tienen un efecto local.

## 5. Umbrales efectivos

La tabla completa por variable y escenario está en la sección 13.8 del documento de la base.

- **Humedad:** la condición base plena termina en 12,5 % y el bloqueo empieza en 14,0 % inclusive, no "más de 14 %".
- **Temperatura:** la corrección empieza en 24 °C y el monitoreo en 14 °C.
- **HR del almacén:** la corrección empieza en 56 % sin plan y en 57,5 % con plan.

## 6. Defectos detectados y corregidos durante la verificación

1. **Unión de términos contiguos.** El máximo de Zadeh creaba un valle de 0,5 en la frontera interna de "TEMPLADA o CALIDA" (24 °C) y de "CALIDA o MUY_CALIDA" (36 °C). Esto violaba el anclaje. Se usa el término fusionado de la partición, que coincide con la suma acotada.
2. **Cobertura del dictamen.** Con dictamen y plan, 12,75 % se corregía y 13 % se autorizaba, una no monotonía. Un lote más seco que la banda dictaminada se evalúa ahora en su borde inferior.
3. **Implicación con antecedente parcial.** R30.6 quedaba elegible a 12,55 % sin dictamen ni plan. Se hizo explícita la condición HUMEDAD_CONDICIONAL.

Los tres ajustes dejan intacta la equivalencia con δ = 0. Los protegen pruebas nuevas: monotonía por variable en tres escenarios y el invariante "autorizar con monitoreo exige plan vigente".

## 7. Pendiente de validación

- **Anchos δ y cortes-α.** Son política del prototipo, sin fuente publicada. Deben contrastarse con el experto (entrevista o rejilla de repertorio) y, cuando haya datos de campo, calibrarse por sensibilidad sobre casos etiquetados.
- **Endurecimiento sin plan.** Sin plan de monitoreo, grados adversos pequeños que elevan el índice por encima de 25 terminan en corrección. Es coherente con la sección 5, pero conviene confirmar con el experto si se desea ese rigor o un corte mayor para la banda [25, 50).
- **Verificación con PostgreSQL.** Las pruebas de persistencia, API y extremo a extremo requieren PostgreSQL y se ejecutan con `scripts/verificar.ps1`.
