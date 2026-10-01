# Changelog

## 2026-09-30 — Revisión del sistema experto difuso

Registro de los cambios realizados hoy en POSCOSEGRAN-SI-DIFUSO y sus motivos. Se basa en los archivos modificados durante la revisión, incluidos cambios todavía sin commit. El repositorio vecino POSCOSEGRAN-SI se utilizó únicamente como referencia de lectura.

### Correcciones de lógica difusa y validación

| Archivo | Cambio | Motivo |
|---|---|---|
| `backend/src/poscosegran/sistema_experto/difuso.py` | `grado_union` calcula siempre máximo de Zadeh; la construcción compatible de intervalos pasó a `grado_compuesto`. La descripción del intervalo fusionado ya no usa el símbolo de unión como si fuera esa operación. | Las diapositivas distinguen unión máximo de otras construcciones. A 24 °C, la unión de TEMPLADA y CALIDA vale 0,5, mientras el intervalo compuesto vale 1. |
| `backend/src/poscosegran/sistema_experto/lenguaje.py` | `es: [..]` llama a la construcción del intervalo compuesto y lo identifica así en sus soportes. `alguno` sigue calculando OR máximo. | Conservar el anclaje y las decisiones existentes sin atribuir a OR un resultado matemático incorrecto. |
| `backend/src/poscosegran/sistema_experto/difuso.py` | Normalización comprobada dentro del universo de discurso, no en picos exteriores. | Antes se aceptaba como normalizado un término triangular cuyo máximo estaba fuera del universo. |
| `backend/src/poscosegran/sistema_experto/difuso.py` | Rechazo explícito de parámetros de forma no finitos y de universos de salida incompletos, degenerados, invertidos o no finitos. | Evitar configuraciones inválidas y fallos de cálculo al adquirir conocimiento. |
| `backend/src/poscosegran/sistema_experto/difuso.py` | Resolución del centroide exige entero entre 101 y 10001; rechaza booleanos, fracciones, texto y tamaños excesivos. | Evitar truncamientos silenciosos, excepciones de conversión y asignación descontrolada de memoria. El modelo vigente conserva sus 1001 puntos. |
| `backend/src/poscosegran/sistema_experto/base_conocimiento.py` | Los valores Decimal deben ser finitos; los errores iniciales de parámetros se reportan como `BaseInvalida` antes de comparar restricciones. | NaN/infinito podían escapar a la validación o provocar errores aritméticos en vez de una propuesta rechazada con explicación. |
| `backend/src/poscosegran/sistema_experto/serializacion.py` | Lectura explícita de fechas obligatorias en evaluación, extremos de intervalos y vencimiento de dictamen. | No reconstruir hechos incompletos con fechas `None` donde el dominio exige una fecha. Las fechas opcionales siguen admitiendo ausencia. |

### Interfaz y contrato

| Archivo | Cambio | Motivo |
|---|---|---|
| `docs/openapi.json` | Se incorpora el contrato OpenAPI generado de la API actual. | El directorio estaba ignorado y el contrato verificable no quedaba incluido en Git. |
| `src/api/contrato.ts` | Regeneración desde OpenAPI, incluyendo inferencia difusa, activaciones, pertenencias, cortes y origen. | Los tipos de la interfaz estaban desactualizados respecto a la API difusa. |
| `src/views/Resultado.tsx` | Panel Mamdani con índice, origen y borrosidad; detalles de μ, activación [inf,sup], consecuentes y alturas agregadas. Motivos y evidencia muestran grados; explicación y tabla R30 muestran α y cortes. | Hacer verificable y presentable el razonamiento difuso que ya calcula el backend. |
| `src/views/Resultado.tsx` | Aclaración de que pertenencia e índice no son probabilidades ni porcentajes de inocuidad. Distingue orientación del índice y decisión final de seguridad. Conserva manejo de evaluaciones históricas sin inferencia. | Evitar una interpretación equivocada de los números y mantener compatibilidad con historial. |
| `src/views/Conocimiento.tsx` | Título de reglas corregido de R01–R30 a R01–R52 y resolución R30. | La lista ya contenía 52 reglas, pero su encabezado anunciaba solo 30. |
| `.gitignore` | Excepción para `docs/openapi.json` y exclusión de `/tmp/`. | Versionar el contrato generado sin incluir las extracciones temporales de las diapositivas; se conserva la exclusión previa de los PDF. |

`src/campos.json` se regeneró y comprobó, sin diferencias de contenido.

### Despliegue y permisos

| Archivo | Cambio | Motivo |
|---|---|---|
| `backend/scripts/render_prepare.py` | Respeta la URL de migraciones separada de la URL de aplicación y normaliza el prefijo PostgreSQL. Conserva fallback para instalaciones existentes con una sola conexión. | Una API con credencial restringida no debe intentar crear/alterar tablas con esa credencial. |
| `backend/scripts/render_prepare.py` | La carga inicial recibe la conexión administrativa solo en su proceso hijo; una versión ya activa no se reemplaza por la semilla. | Preparar despliegues sin restablecer conocimiento aprobado ni cambiar la conexión de ejecución de la API. |
| `backend/sql/permisos_aplicacion.sql` | Permiso de actualización de la columna `motivo` en versiones de conocimiento. | El descarte de propuestas modifica ese campo; el SQL de despliegue no tenía el mismo permiso que el preparador local. |

### Correcciones de análisis estático y tipos

La revisión inicial encontró siete incidencias Ruff y 21 errores de Mypy. Se corrigieron sin cambiar los criterios de decisión del dominio:

| Archivo | Ajuste y razón |
|---|---|
| `backend/src/poscosegran/api/local.py` | Separación del nombre de usuario recibido y la cuenta persistida, evitando reutilizar una variable con tipos incompatibles. |
| `backend/src/poscosegran/api/rutas/adquisicion.py` | Tipos de identidad/base y acceso al contenido validado por el cargador en lugar de indexar contenido persistido opcional. |
| `backend/src/poscosegran/api/rutas/evaluacion.py` | Tipos explícitos de pasos y ramas explicadas para sus transformaciones al contrato. |
| `backend/src/poscosegran/api/rutas/seguimiento.py` | Tipo explícito `AmbitoUnidad` para las revisiones del ámbito. |
| `backend/src/poscosegran/db/sesion.py` | Anotaciones del callback de conexión DBAPI. |
| `backend/src/poscosegran/dominio/valores.py` | Tipo concreto del umbral de evidencia, coherente con el objeto de dominio. |
| `backend/src/poscosegran/servicios/aplicabilidad.py` | Tipo `Tri` explícito del retorno booleano del dominio. |
| `backend/src/poscosegran/servicios/presentacion.py` | Conversión numérica limitada a Decimal/int/float; valores incompatibles producen error explícito. |
| `backend/src/poscosegran/sistema_experto/calculos.py` | Aserción de lecturas no nulas después de comprobar que un intervalo está documentado. |
| `backend/src/poscosegran/esquemas/__init__.py` | Excepción Ruff puntual para la reexportación pública intencional. |
| `backend/scripts/generar_casos_referencia.py` | Excepción E402 documentada para importar utilidades después de preparar el path de pruebas. |

### Pruebas añadidas y corregidas

- **`backend/tests/test_revision_teoria.py`: 39 casos nuevos.** Unión versus intervalo compuesto, OR real en el evaluador, parámetros no finitos, normalización fuera del universo, universos inválidos, resolución inválida/excesiva y comprobación individual de R31–R52. Se verifican los vetos, correcciones, aviso R47 y vencimiento comercial separado de la vida estimada.
- **`backend/tests/test_preparacion_despliegue.py`: dos casos nuevos.** Migración con credencial administrativa, carga inicial con dicha credencial y conservación de la versión activa.
- **`backend/tests/test_adquisicion_api.py`: fixture actualizada.** Las propuestas de humedad máxima de 13,06 % violaban la rampa de 0,5 % sobre el umbral base de 13 %. Los ejemplos válidos ahora parten de 14,06 %. No se relajó la restricción de la base.
- **`tests/e2e/flujo.spec.ts`: comprobación del panel difuso.** Sobre el flujo real de cuarentena verifica Mamdani, la advertencia de interpretación, R18 con activación plena y altura CRITICA = 1.

### Documentación

| Archivo | Cambio y propósito |
|---|---|
| `REVISION-SISTEMA-DIFUSO.md` | Nuevo informe con las siete presentaciones, correspondencia teoría/código, revisión de cada R01–R52 y rama R30, pruebas, límites de validación y ejemplos para exposición. |
| `PLAN-DESPLIEGUE.md` | Nuevo plan: Render + Supabase recomendado, Cloudflare Pages y otras combinaciones, Amazon EC2, cuotas gratuitas comprobadas en fuentes oficiales, variables, migraciones, Auth/JWKS, roles, ensayo y respaldo. |
| `README.md` | Corrige la versión cargada a base difusa 3.1 y enlaza revisión, plan y changelog. |
| `backend/pyproject.toml` | Descripción actualizada al sistema experto difuso; elimina la descripción histórica de etapas 6/7. |
| `knowledge/POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md` | Sección 13.2 y nota histórica aclaradas: intervalo compuesto no equivale a unión máximo. Incluye sintaxis explícita y cómo interpretar las fichas abreviadas R06/R08/R16. |
| `knowledge/POSCOSEGRAN_informe_impacto_difuso.md` | Aclara esa misma distinción y registra que la comprobación PostgreSQL/navegador ya se ejecutó en esta revisión. |
| `changelog.md` | Este registro, creado al nivel de README con fecha, cambios, razones y evidencia. |

### Resultado de validación

- Suite completa con PostgreSQL 16 aislado: **593 aprobadas y una omisión**, correspondiente al chequeo de credencial restringida.
- Ese chequeo pasó por separado con `poscosegran_app`; la nueva prueba OR/intervalo, añadida después de la suite completa, también pasó. **Los 595 casos del conjunto final quedaron comprobados entre esas ejecuciones.**
- Los **242 casos originales** coincidieron con la base nítida 2.0 del repositorio vecino. La regresión δ = 0, conservadurismo, monotonía y centroides también pasó.
- Ruff, Mypy estricto (63 archivos), ESLint y TypeScript: sin errores.
- Contrato regenerado dos veces: sin diferencias entre regeneraciones.
- Build Vite de producción correcto.
- Cinco migraciones aplicadas y `alembic check` sin operaciones pendientes.
- Playwright: **3/3 contra API local y 3/3 contra el stack Docker completo**.
- Docker: imágenes de API/web construidas, inicialización completada y servicios saludables. Preparador de despliegue probado además con credenciales separadas y versión activa existente.
- Advertencia de deprecación Starlette/AnyIO observada en pruebas; no causó fallos.

### Compatibilidad y alcance

Se conservaron las reglas operativas, los valores de parámetros del dominio, los casos congelados y las decisiones válidas existentes. No se añadieron tolerancias a límites comerciales ni se reemplazó la resolución de seguridad por el centroide. No se cambiaron archivos del repositorio original, no se eliminaron datos existentes y no se publicaron recursos de nube.

Las dependencias y herramientas necesarias se instalaron para verificar el proyecto; los entornos, extracciones PDF, capturas y datos de prueba permanecen fuera de Git. Las pruebas utilizaron un proyecto Docker y un volumen propios. Al finalizar se detuvieron los servidores temporales y el stack de pruebas, conservando el volumen. El despliegue y la validación agrícola de políticas siguen siendo pasos posteriores descritos en sus documentos.
