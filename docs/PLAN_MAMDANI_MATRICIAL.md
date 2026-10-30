# Plan de conversión a Mamdani matricial

Fecha: 29 de octubre de 2026. Alcance autorizado: aplicación, conocimiento, pruebas, cuatro corridas persistidas, informe Word, guía de ingreso y presentación.

## Diseño acordado

Un nivel Mamdani tipo 1. Matriz no hermética de 256 reglas (humedad del grano × temperatura del grano × HR del almacén × estado físico y sanitario; cuatro etiquetas por entrada). Matriz hermética de 64 reglas, excluyendo HR ambiental. Las dos matrices son alternativas por modalidad; no se encadenan. AND mínimo, implicación mínimo, agregación máximo y centroide exacto de funciones lineales por tramos.

La cuarta entrada es una inspección categórica: SIN_HALLAZGOS, DANO_FISICO, INDICIOS_BIOLOGICOS y HALLAZGO_CRITICO. Tiene funciones características 0/1; no se inventa una intensidad continua de moho ni una probabilidad sanitaria. Las otras tres entradas usan funciones triangulares y trapezoidales solapadas. La inspección exige fecha, método y descripción. Los indicios no equivalen a infestación confirmada. Moho visible o insectos vivos observados sustentan el estado crítico según el protocolo declarado.

Las referencias de humedad, temperatura y HR proceden de las fuentes S01–S04 revisadas. Los vértices específicos y la matriz son decisiones del prototipo, no umbrales publicados para chulpi. El modelo produce un índice de intervención y cinco recomendaciones; no certifica inocuidad, ausencia de micotoxinas ni duración segura.

Los datos faltantes o inválidos generan un resultado no calculable; no se sustituyen por cero. En hermético se exige evidencia vigente de integridad y procedimiento de medición/inspección interna. Estas son validaciones de aplicabilidad y captura, no reglas de decisión adicionales. No se ejecutarán R01–R52 ni MF01–MF14.

## Secuencia de trabajo

1. Conservar un respaldo local de los documentos originales y registrar el diseño. Revisar contratos, persistencia y pruebas existentes.
2. Generar y versionar las 320 reglas explícitas, sus fuentes, las funciones de pertenencia y cuatro casos de referencia. Comprobar cantidad, unicidad, cobertura, extremos, monotonía lingüística y sensibilidad continua.
3. Reemplazar la agenda documental por inferencia matricial directa. Mantener la infraestructura de identidad, permisos, revisiones, idempotencia, observaciones, trazas e historial inmutable.
4. Simplificar la captura a las entradas del modelo y a su evidencia. Actualizar explicación, curvas, matriz navegable y catálogo. Retirar constructores y pantallas de reglas documentales del flujo activo.
5. Verificar funciones con cálculo independiente, modelo completo, API contra PostgreSQL, permisos, idempotencia, reproducción de trazas y recorrido de navegador. Conservar resultados y errores corregidos en un registro de verificación.
6. Registrar cuatro lotes de demostración mediante la API local y comprobar sus evaluaciones y auditoría directamente en PostgreSQL. Separar el historial de demostración de las bases usadas por las pruebas destructivas.
7. Reescribir el informe conservando su estructura académica y eliminando las fotografías de las corridas. Preparar la guía de cuatro lotes y una presentación propia orientada por la estructura del PDF de referencia.
8. Renderizar e inspeccionar los documentos y las diapositivas. Redactar el resumen del cambio con resultados verificables y limitaciones.

## Cuatro corridas

Se seleccionarán un caso favorable hermético, un caso no hermético de transición con recomendación de vigilancia, un caso de condiciones adversas que requiera acondicionamiento y un caso sanitario crítico. Los valores y centroides se fijarán después de ejecutar el modelo, no para reproducir artificialmente los índices anteriores. Cada corrida tendrá identificación, entradas, evidencia, matriz aplicable, pertenencias, reglas activadas, curva, centroide y recomendación.

## Conservación de datos

Las nuevas evaluaciones utilizarán una nueva versión del conocimiento. No se borrarán evaluaciones, usuarios o incidencias anteriores para limpiar el código. El retiro de referencias antiguas se aplicará al motor activo, interfaz y entregables. Las versiones históricas en PostgreSQL conservan su procedencia; no se presentarán como resultados del nuevo modelo. El despliegue público se realizará únicamente cuando exista una versión concreta verificada y dentro de la autorización del usuario.

## Criterios de cierre

- Exactamente 256 y 64 antecedentes únicos, sin reglas documentales ejecutables ni segunda etapa de decisión.
- Hallazgo sanitario crítico sin compensación por condiciones ambientales favorables.
- Sin regiones sin cobertura dentro de los dominios; desconocido e inválido nunca equivalen a favorable.
- Captura, cálculo, consulta e historial enlazados con PostgreSQL real.
- Cuatro corridas reproducibles y registradas; informe y presentación con el mismo modelo, cantidades y resultados.
- Informe y guía Word renderizados sin fotografías en las corridas; entrega de presentación editable y resumen de verificación.
