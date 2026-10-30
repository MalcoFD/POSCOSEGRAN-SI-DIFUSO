# Refactor del sistema POSCOSEGRAN

La base vigente 6.0 aplica una inferencia Mamdani directa por modalidad. Se publican 256 reglas no herméticas y 64 herméticas, con parámetros 2.0 y motor 4.0.0-matricial. No se ejecutan las producciones documentales ni la segunda etapa de decisión del diseño sustituido.

## Modelo y flujo

Las entradas son humedad del grano, temperatura del grano, HR del almacén y estado físico y sanitario. H, T y HR tienen cuatro etiquetas solapadas. La inspección tiene cuatro categorías observadas con pertenencias 0/1: sin hallazgos, daño físico, indicios biológicos y hallazgo crítico. Moho visible o insectos vivos observados corresponden al último estado.

En hermético se excluye HR y se documentan barrera íntegra y procedimiento interno. Estos metadatos validan la aplicabilidad; no añaden puntuaciones ni reglas de recomendación. Los desconocidos, las fechas futuras o vencidas y la evidencia sanitaria ausente dejan el cálculo pendiente sin índice.

El flujo es captura, validación, fuzzificación, selección de matriz, activación mínima, recorte mínimo, agregación máxima, centroide exacto e interpretación. Las cinco recomendaciones son conservación favorable, monitoreo, acondicionamiento, suspensión y separación sanitaria. La fase identifica el registro y no cambia la matriz.

## Integración de la aplicación

Se conserva la navegación, el menú lateral y la hoja de estilos del frontend original. Se adaptan la captura de evaluación, las pertenencias, el resultado, el catálogo navegable y la gestión de propuestas al contrato matricial. El servidor calcula el resultado; el navegador lo representa.

La API conserva identidad, permisos, revisiones, borradores, idempotencia e historial. La migración 0008 incorpora suspensión sin retirar las recomendaciones de registros anteriores. No se reescriben ni eliminan evaluaciones históricas. Una incidencia o evento puede invalidar la utilización de una autorización, conservando el centroide emitido.

Las versiones antiguas conservan su registro. El motor nuevo devuelve una respuesta 409 explicada cuando se solicita recalcular un modelo anterior, en lugar de ejecutar otro motor o producir un error 500. La evaluación persistida sigue disponible mediante la consulta de resultados.

## Documentos y cuatro corridas

`INFORME_ACTUALIZADO.docx` se editó desde el paquete original, conservando carátula con escudo, encabezado, pie, tamaño de página, márgenes, estilos y los ocho apartados académicos. Se actualizaron variables, funciones, reglas, operadores, implementación, cuatro corridas sin fotografías, conclusiones y referencias. El anexo presenta las 320 reglas en cortes 4×4.

`Guia_ingreso_4_lotes_POSCOSEGRAN.docx` deriva de la guía original. Cada lote tiene tablas completas de valor, fecha, método y evidencia, pasos de las pantallas, opciones visibles, pertenencias, reglas, cálculo esperado, consulta del historial y espacio para registrar la recreación de un compañero. Se mantiene el formato del original y se actualizan su encabezado y versión.

| Corrida | Datos | Centroide | Resultado |
|---|---|---:|---|
| M320-L01 | Hermético, H12, T10, sin hallazgos |4,666667|Conservar con controles ordinarios|
| M320-L02 | No hermético, H12, T18, HR50, sin hallazgos |19,165217|Monitoreo reforzado|
| M320-L03 | No hermético, H13,5, T25, HR60, sin hallazgos |81|Suspender almacenamiento normal|
| M320-L04 | No hermético, H12, T10, HR50, hallazgo crítico |97,666667|Separar y solicitar evaluación técnica|

Las cuatro corridas son simuladas y están registradas mediante HTTP en PostgreSQL local. Se comprobaron cuatro evaluaciones y cuatro auditorías, sin duplicar una solicitud repetida con la misma clave. La cuarta unidad mantiene una incidencia abierta. Los identificadores y fechas están en EVIDENCIA_CORRIDAS_4.json. La actualización de diapositivas queda a cargo del equipo.

## Verificación

La suite final aprobó 444 pruebas con PostgreSQL real y omitió una comprobación de privilegios por usar credencial administrativa. Las seis pruebas de esquema, incluida esa comprobación, aprobaron por separado con la credencial de aplicación. Las 51 operaciones HTTP tuvieron respuestas exitosas en los recorridos de prueba, sin respuestas 500 en la ejecución final.

Pasaron cinco pruebas de navegador en desarrollo local y los mismos cinco recorridos en el stack Docker: cuatro capturas completas con resultado e historial y un recorrido de administrador, técnico e ingeniero. También aprobaron Ruff, Mypy, TypeScript, ESLint, la construcción del frontend y Alembic sin diferencias pendientes de esquema.

El diagnóstico de superficie examinó 119.808 puntos y 344.000 comparaciones vecinas. No observó descensos de categoría en esa malla; sí oscilaciones locales del centroide, con máximos de 1,099292 y 0,790909 puntos. Esto se documenta sin afirmar monotonía global. Las curvas e interacciones requieren revisión especializada y validación de campo para chulpi.

Los resultados consolidados se conservan localmente en VERIFICACION_MATRICIAL.json, excluido de Git. Los directorios temporales y capturas de prueba se eliminan después de trasladar esa evidencia.

## Limpieza y despliegue

Se retiran módulos y componentes del motor sustituido, pruebas que exigían ese motor, documentación obsoleta, la guía de cinco lotes, el consolidado anterior, temporales, resultados de prueba y metadatos egg-info generados. Se conservan las pruebas activas y las ocho migraciones porque son necesarias para verificar e instalar el esquema. El SQL de roles, permisos y RLS opcional mantiene referencias de uso en la configuración de seguridad y despliegue.

Se verificó la construcción de las imágenes y el arranque con PostgreSQL, inicialización y Nginx. El inicializador aplica migraciones y carga el conocimiento de forma idempotente antes de arrancar la API. Se corrigió el respeto de POSCOSEGRAN_KNOWLEDGE para encontrar los 320 casos de referencia dentro del contenedor.

Para AWS, el compañero debe publicar la versión del repositorio y ejecutar el procedimiento existente de despliegue de la API en ECS. Amplify puede reconstruir el frontend al recibir cambios en la rama configurada; ese build no actualiza por sí solo la API. La infraestructura y los secretos existentes se conservan. Esta tarea verifica el artefacto de despliegue localmente; no ejecuta cambios sobre AWS.

La revisión automática bloqueó el borrado forzado. Se eliminaron los archivos sin forzar y solo permanecen vacíos los directorios locales ocultos `tmp`, `dist` y `.ruff_cache`, excluidos de Git y del despliegue.

## Documentación publicada y entrega al equipo

En `docs` solo se versionan `openapi.json`, este resumen y [REGLAS_ACTUALES.md](REGLAS_ACTUALES.md). El detalle de reglas incluye las funciones de pertenencia, los 320 antecedentes y consecuentes mediante matrices con identificadores, la inferencia, los cuatro ejemplos y los límites del modelo.

El informe original corregido, la guía de cuatro lotes, los manuales complementarios, los PDF y las evidencias JSON permanecen en el equipo local. Se excluyen mediante `.gitignore`, sin borrar sus archivos. El responsable del proyecto enviará los informes por separado a su equipo.
