<p align="center">
  <img src=".github/assets/banner-poscosegran.png" alt="POSCOSEGRAN-DIFUSO: maíz chulpi y flujo de mediciones, interfaz web, API FastAPI y motor Mamdani de conservación y decisión; PostgreSQL conectado con la API" width="100%" />
</p>

<div align="center">
  <img src="public/favicon.svg" alt="Símbolo de POSCOSEGRAN" width="48" />

# POSCOSEGRAN-DIFUSO

**Sistema de inferencia difusa para el almacenamiento poscosecha de maíz chulpi.**

React · FastAPI · Python · PostgreSQL · Mamdani tipo 1

[Aplicación en AWS](https://main.d3lylniuaxtfc1.amplifyapp.com/) · [Inicio rápido](#inicio-rápido) · [Uso](#cómo-usar-el-sistema) · [Modelo difuso](#modelo-difuso) · [Arquitectura](#arquitectura) · [Verificación](#verificación)

</div>

POSCOSEGRAN combina mediciones del grano, inspecciones del almacén y evidencia documentada para orientar decisiones de almacenamiento. Permite registrar unidades, evaluar sus condiciones, explicar el resultado y dar seguimiento a acciones e incidencias.

Proyecto académico de **Sistemas Inteligentes**, Facultad de Ingeniería de Sistemas e Informática, **Universidad Nacional Mayor de San Marcos**. Se relaciona con el **ODS 2, meta 2.3**, por su propósito de apoyar la conservación de la producción de pequeños agricultores.

> [!NOTE]
> Este README concentra la documentación de uso, instalación, arquitectura y mantenimiento. La fuente ejecutable del modelo se conserva en los archivos YAML y el contrato HTTP en `docs/openapi.json`.

## Qué ofrece

- **Captura guiada:** mediciones, procedimiento, verificaciones e historial por unidad.
- **Inferencia explicable:** severidad de conservación y decisión final mediante dos niveles Mamdani.
- **Trazabilidad:** observaciones, reglas, fuentes, pertenencias, curvas y centroides.
- **Seguimiento:** controles, eventos, planes, dictámenes y resolución técnica de incidencias.
- **Inspecciones compartidas:** reutilización contextual de infraestructura e higiene del mismo almacén.
- **Conocimiento versionado:** propuestas, simulación de impacto y activación revisada.
- **Permisos por rol:** acceso a recursos propios o asignados, comprobado en el servidor.

| Modelo vigente | Contenido |
| --- | --- |
| Base de conocimiento | **5.0** |
| Motor difuso | **3.0.0-mamdani** |
| Conservación | 4 mediciones; 3 aplicables en hermético; **9 reglas D01–D09** |
| Decisión final | 11 antecedentes derivados o de contexto; **14 reglas MF01–MF14** |
| Total difuso | **23 reglas** y **7 acciones finales** |
| Fundamento documental | **52 reglas R01–R52**, referencias S01–S09 |

Los 94 campos del catálogo incluyen mediciones, verificaciones y gestión; no son 94 entradas difusas simultáneas. Las reglas documentales y las reglas Mamdani cumplen funciones diferentes.

## Despliegue en AWS

La aplicación fue desplegada en **Amazon Web Services** para su demostración y revisión académica. El acceso directo al frontend de la rama `main` es:

### [Abrir POSCOSEGRAN-DIFUSO](https://main.d3lylniuaxtfc1.amplifyapp.com/)

El enlace abre la aplicación web; para usar los módulos se requiere una sesión y los permisos del rol correspondiente. La contraseña del entorno AWS puede diferir de la local y la administra el responsable del despliegue.

La infraestructura y el proceso de publicación están definidos en [`infra/terraform/`](infra/terraform/), [`amplify.yml`](amplify.yml) y [`scripts/desplegar_aws.ps1`](scripts/desplegar_aws.ps1):

| Componente | Servicio y función |
| --- | --- |
| Frontend React/Vite | **AWS Amplify Hosting**: compilación desde GitHub, publicación de `dist/`, HTTPS y reescritura de rutas de la SPA |
| Acceso al backend | **Amazon API Gateway HTTP API**: endpoint HTTPS con integración privada mediante VPC Link y Cloud Map |
| API FastAPI | **Amazon ECS Fargate**: ejecución del contenedor de la API después de completar la inicialización |
| Imágenes de contenedor | **Amazon ECR**: almacenamiento de la imagen del backend |
| Persistencia | **Amazon RDS for PostgreSQL**: base de datos en la red privada |
| Configuración privada | **AWS Systems Manager Parameter Store**: credenciales y secretos suministrados a los contenedores |
| Registros | **Amazon CloudWatch Logs**: registros de inicialización y API |

```mermaid
flowchart LR
    N[Navegador] --> F[Amplify Hosting: frontend HTTPS]
    F --> G[API Gateway HTTPS]
    G --> V[VPC Link y Cloud Map]
    V --> A[ECS Fargate: API FastAPI]
    A --> B[(RDS PostgreSQL privado)]
    S[Parameter Store] --> A
    A --> L[CloudWatch Logs]
```

El frontend utiliza `VITE_AUTH_MODE=local` para la demostración y `VITE_API_URL` con el endpoint HTTPS del backend, según la configuración Terraform. La API usa el entorno `pruebas`, verifica los permisos en el servidor y recibe las credenciales desde Parameter Store. El contenedor `inicializar` prepara roles, migraciones, usuarios y conocimiento; la API arranca solo si esa tarea termina correctamente. Las credenciales administrativas no se entregan al navegador ni al contenedor principal de la API.

<details>
<summary><strong>Actualizar y operar el despliegue</strong></summary>

Para administrarlo se requieren acceso autorizado a la cuenta AWS, **AWS CLI v2**, **Terraform ≥ 1.6**, **Docker Desktop** y la configuración privada del entorno. `infra/terraform/terraform.tfvars.example` sirve como plantilla; `terraform.tfvars`, el estado y las credenciales permanecen fuera de Git. La región predeterminada de la configuración es `us-east-1` y puede sobrescribirse.

Desde la raíz, para aplicar infraestructura, construir y publicar la imagen en ECR, actualizar ECS y solicitar la compilación de Amplify:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/desplegar_aws.ps1
# Si se utiliza un perfil de AWS CLI:
powershell -ExecutionPolicy Bypass -File scripts/desplegar_aws.ps1 -Perfil NOMBRE_DEL_PERFIL
```

Para actualizar únicamente el backend sobre la infraestructura existente:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/desplegar_aws.ps1 -SaltarTerraform -SaltarFrontend
```

Amplify tiene activada la compilación automática de la rama configurada (`main` por defecto). `amplify.yml` instala Node.js 22 y pnpm 10.24.0, restaura dependencias y ejecuta `pnpm build`. Las rutas internas de la SPA se reescriben a `index.html`.

Las salidas de Terraform permiten consultar las direcciones y los identificadores necesarios para diagnóstico:

```powershell
terraform -chdir=infra/terraform output -raw frontend_url
terraform -chdir=infra/terraform output -raw api_url
terraform -chdir=infra/terraform output -raw ecs_cluster
terraform -chdir=infra/terraform output -raw ecs_servicio
```

Comprueba el endpoint de API seguido de `/salud/bd` para revisar la conexión con PostgreSQL. Consulta los trabajos de Amplify si falla la publicación del frontend y los registros de CloudWatch si fallan la inicialización o la API. El responsable autorizado puede consultar la salida `comando_password_login` para obtener el procedimiento de recuperación de la contraseña de demostración desde SSM; su valor no se publica en este README.

Los recursos AWS generan costos mientras permanezcan activos. Revisa el presupuesto, la facturación y los respaldos antes de pausar o retirar el entorno. La aplicación publicada sigue siendo una demostración académica; el acceso compartido de pruebas no sustituye una configuración de identidad de producción.

</details>

## Inicio rápido

### Opción 1 · Aplicación completa con Docker

Requiere **Docker Desktop iniciado** con Docker Compose. Desde la raíz, en PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/iniciar_docker.ps1
```

El script crea `backend/.env` si no existe, genera el secreto JWT local y construye los servicios. La inicialización prepara roles SQL, aplica migraciones, carga la semilla difusa y registra los usuarios de demostración. Se puede repetir sin borrar datos ni duplicar el catálogo.

| Servicio | Dirección |
| --- | --- |
| Aplicación | [http://localhost:8080](http://localhost:8080) |
| Salud de API y PostgreSQL | [http://localhost:8080/salud/bd](http://localhost:8080/salud/bd) |
| Documentación interactiva | [http://localhost:8080/documentacion](http://localhost:8080/documentacion) |
| PostgreSQL local | `127.0.0.1:55432` |

El contenedor `inicializar` debe terminar con **Exited (0)**: es una preparación completada correctamente. `bd`, `api` y `web` deben permanecer saludables.

```powershell
docker compose --env-file backend/.env ps --all
docker compose --env-file backend/.env logs -f inicializar api web

# Detener conservando los datos
docker compose --env-file backend/.env down
```

> [!IMPORTANT]
> El volumen `poscosegran_datos` conserva los registros. `down --volumes` lo elimina: no lo uses para detener una demostración que quieras conservar.

### Acceso de demostración

| Usuario local | Rol | Alcance |
| --- | --- | --- |
| `productor` o alias `testeo` | Productor | Sus almacenes, lotes y unidades |
| `tecnico` | Técnico | Recursos de almacenes o lotes asignados |
| `administrador` | Administrador | Asignar y revocar acceso de técnicos |
| `ingeniero` | Ingeniero del conocimiento | Proponer, simular y gestionar versiones del conocimiento |

La contraseña vigente está en **`POSCOSEGRAN_AUTH_LOCAL_PASSWORD` de `backend/.env`**. En un entorno nuevo generado por los preparadores incluidos, su valor inicial es `testeo`; los archivos existentes se conservan. El técnico requiere una asignación. El administrador y el ingeniero no adquieren acceso general a las evaluaciones productivas por su rol.

### Opción 2 · Desarrollo local

Requisitos: **Python 3.13**, **Node.js 22**, **pnpm 10.24.0** y Docker Desktop para PostgreSQL. Las versiones de herramientas están declaradas en `.mise.toml`.

```powershell
# Desde la raíz
docker compose up -d bd
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
pnpm.cmd install --frozen-lockfile
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
```

Reutiliza el entorno virtual si ya existe. Alternativa con `uv`: `uv venv backend/.venv --python 3.13` y `uv pip install --python backend/.venv/Scripts/python.exe -e "backend[dev]"`.

Abre dos terminales:

```powershell
# Terminal 1: API
cd backend
.venv/Scripts/python.exe -m uvicorn poscosegran.api.app:crear_app --factory --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: frontend, desde la raíz
pnpm.cmd dev
```

Aplicación: [http://localhost:8443](http://localhost:8443). API: [http://127.0.0.1:8000/documentacion](http://127.0.0.1:8000/documentacion). Vite dirige `/api` y `/auth/local` al backend; el preparador crea `.env.local` para el acceso local.

## Cómo usar el sistema

1. **Registrar recursos.** Crea o selecciona almacén, lote y unidad. Una unidad es un lote en un recipiente dentro de un almacén; condiciones diferentes requieren unidades distintas.
2. **P1 · Identificación.** Comprueba fase de ingreso o seguimiento, modalidad hermética o no hermética y fundamento del clima.
3. **P2 · Mediciones y plazo.** Registra humedad, temperatura, HR cuando aplica, defectos, procedimiento de medición, historial, vida previa y salida prevista.
4. **P3 · Verificaciones.** Completa grano, recipiente, estiba, higiene, infraestructura y demás comprobaciones. Puede reutilizarse una inspección vigente del mismo almacén dentro de su alcance. Revisa antes de enviar.
5. **P4 · Resultado.** Consulta la acción, los pendientes y el próximo control. Los paneles Mamdani muestran las reglas, las curvas agregadas y los centroides de ambos niveles.
6. **Seguimiento.** Registra controles, eventos y planes. Después de corregir, documenta la nueva observación y reevalúa. Una resolución técnica no autoriza por sí sola el almacenamiento.

Cada dato aportado requiere **valor, fecha y método**, además de la evidencia aplicable. **No se sabe** conserva la incertidumbre; **No** es una observación negativa conocida. **No aplica** exige motivo y contexto compatible. En hermético, la HR ambiental queda excluida del núcleo.

Los borradores se conservan en la pestaña y, opcionalmente, en el servidor. Cerrar la pestaña elimina su almacenamiento de sesión. Si una petición tiene resultado incierto por un fallo de red, reintenta la misma operación sin modificar su contenido para conservar la idempotencia.

Las fechas se almacenan en UTC y el historial se presenta en `America/Lima`. Al reevaluar, conserva la vida acumulada documentada de la unidad: no la reduzcas a un valor inicial ni sumes otra vez intervalos ya incluidos.

### Escenarios de demostración

Son **resultados esperados** de los datos simulados de la guía de ingreso. El resumen no sustituye sus verificaciones completas.

| Caso | Condición distintiva | Regla final | Resultado esperado | Centroide |
| --- | --- | --- | --- | ---: |
| DEMO-L01 | Hermético; humedad 12 %, grano a 10 °C; evidencia completa | MF14 | Autorizar almacenamiento | 4,667 |
| DEMO-L02 | No hermético; humedad 12 %, grano a 18 °C; plan cada 5 días | MF09 | Autorizar con monitoreo | 28,000 |
| DEMO-L03 | Hermético; separación al piso de 0,05 m | MF05 | Corregir y reevaluar | 52,000 |
| DEMO-L04 | No hermético; humedad confirmada de 15 %; fase ingreso | MF02 | Bloquear ingreso | 81,000 |
| DEMO-L05 | Moho visible y olor anormal presentes | MF01 | Cuarentena | 97,667 |

En la unidad existente DEMO-L01 la vida previa de la guía es 0,20; en las unidades nuevas de los otros casos es 0,10. Recalcula las fechas para cada sesión. Una cuarentena abierta requiere resolución técnica, aunque una medición posterior sea favorable.

## Modelo difuso

### Primer nivel · Conservación

Combina las mediciones aplicables y obtiene una **severidad conjunta de 0 a 100**.

| Entrada | Universo | Bajo | Medio | Alto |
| --- | --- | --- | --- | --- |
| Humedad del grano, % b.h. | [0; 100] | Trap(0; 0; 12,5; 13) | Tri(12,5; 13; 13,5) | Trap(13; 13,5; 100; 100) |
| Temperatura del grano, °C | [−30; 90] | Trap(−30; −30; 20; 25) | Tri(20; 25; 30) | Trap(25; 30; 90; 90) |
| HR del almacén, % HR | [0; 100] | Trap(0; 0; 50; 60) | Tri(50; 60; 70) | Trap(60; 70; 100; 100) |
| Granos defectuosos, % masa | [0; 100] | Trap(0; 0; 6; 7) | Tri(6; 7; 8) | Trap(7; 8; 100; 100) |

`Tri(a; b; c)` indica una función triangular; `Trap(a; b; c; d)`, una trapezoidal. Los vértices repetidos representan hombros. Los universos son dominios de cálculo, no intervalos recomendados de almacenamiento.

La humedad requiere medición confirmada. En hermético se excluye HR y participan tres mediciones. Una humedad de 12,7 % tiene pertenencia **0,6 a bajo** y **0,4 a medio**: son compatibilidades lingüísticas, no probabilidades.

| Reglas | Interpretación |
| --- | --- |
| D01–D02 | Todas las mediciones aplicables bajas → conservación baja, según modalidad |
| D03–D04 | Alguna medición media → conservación media |
| D05–D06 | Alguna medición alta → conservación alta |
| D07–D09 | Interacciones humedad–temperatura, humedad–HR y temperatura–HR medias → conservación alta |

Consecuentes: bajo `Trap(0; 0; 10; 25)`, medio `Tri(20; 50; 80)` y alto `Trap(70; 85; 100; 100)`. El centroide se vuelve a fuzzificar en el segundo nivel mediante bajo `[0,0,20,35]`, medio `[20,45,65]` y alto `[50,65,100,100]`.

### Segundo nivel · Decisión

Las once entradas finales son `cuarentena`, `suspension`, `correccion`, `pendientes`, `evidencia`, `plan`, `monitoreo`, `condicional`, `fase`, `conservacion` y `baja_completa`. Integran los hallazgos documentales, el plazo, el plan y la salida anterior.

| Reglas | Condición resumida | Consecuente |
| --- | --- | --- |
| MF01 | Cuarentena solicitada o episodio abierto | Cuarentena |
| MF02–MF04 | Sin cuarentena; suspensión según fase | Bloquear, retirar o sin conclusión automática |
| MF05 | Sin cuarentena ni suspensión; corrección exigida | Corregir y reevaluar |
| MF06–MF07 | Sin las anteriores; pendientes o evidencia insuficiente | Sin conclusión automática |
| MF08–MF09 | Evidencia completa, plan y conservación baja; según motivo de seguimiento | Autorizar o autorizar con monitoreo |
| MF10–MF11 | Evidencia completa, plan y conservación media o alta | Monitorear o corregir |
| MF12–MF14 | Evidencia completa y sin plan; según conservación plenamente baja y seguimiento | Corregir o autorizar |

Los antecedentes completos están en [la base difusa](knowledge/difuso/base_conocimiento.yaml). Las negaciones exigen ausencia conocida. Si hay cuarentena, las reglas incompatibles tienen activación cero; una medición favorable no compensa el hallazgo. La falta de plan impide una autorización de monitoreo sin respaldo.

| Centroide final `z` | Acción | Función del consecuente |
| --- | --- | --- |
| 0 ≤ z < 16 | `AUTORIZAR_ALMACENAMIENTO` | Trap(0; 0; 6; 12) |
| 16 ≤ z < 40 | `AUTORIZAR_CON_MONITOREO` | Tri(20; 28; 36) |
| 40 ≤ z < 63 | `CORREGIR_Y_REEVALUAR` | Tri(44; 52; 60) |
| 63 ≤ z < 76 | `SIN_CONCLUSION_AUTOMATICA` | Tri(66; 70; 74) |
| 76 ≤ z < 85 | `BLOQUEAR_INGRESO` | Tri(78; 81; 84) |
| 85 ≤ z < 93,5 | `RETIRAR_LOTE` | Tri(86; 89; 92) |
| 93,5 ≤ z ≤ 100 | `CUARENTENA` | Tri(95; 98; 100) |

El último límite almacenado es 101 para incluir todo el dominio hasta 100. La decisión vigente se obtiene del centroide final; las ramas deterministas de R30 corresponden a versiones históricas.

### Operadores y núcleo en Python

```text
Fuzzificación → activación → implicación → agregación → centroide
                  AND: min       min           max        exacto
                  OR:  max
```

El centroide integra la **envolvente máxima de los conjuntos recortados**, añadiendo vértices, puntos de recorte e intersecciones. No promedia los centroides de las reglas ni utiliza una malla discretizada para decidir.

| Archivo | Responsabilidad |
| --- | --- |
| [motor.py](backend/src/poscosegran/sistema_difuso/motor.py) | `MotorDifuso`: `_conjunto()` evalúa conservación; `_resolver()` invoca la decisión final |
| [pertenencia.py](backend/src/poscosegran/sistema_difuso/pertenencia.py) | Funciones triangulares y trapezoidales, incluidos hombros |
| [reglas.py](backend/src/poscosegran/sistema_difuso/reglas.py) | Activación recursiva por mínimo y máximo |
| [defuzzificacion.py](backend/src/poscosegran/sistema_difuso/defuzzificacion.py) | Envolvente, área y centroide exacto por tramos |
| [decision.py](backend/src/poscosegran/sistema_difuso/decision.py) | Once antecedentes, catorce reglas y clasificación final |
| [base_conocimiento.yaml](knowledge/difuso/base_conocimiento.yaml) | Variables, curvas, reglas y parámetros operativos |
| [catalogo.yaml](knowledge/difuso/catalogo.yaml) | Reglas documentales y referencias |

> [!IMPORTANT]
> Curvas, interacciones y cortes son **políticas del prototipo**, pendientes de calibración agronómica para chulpi. Las fuentes respaldan condiciones y referencias documentales; estos índices no son probabilidades de inocuidad ni certifican ausencia de micotoxinas.

## Arquitectura

```mermaid
flowchart LR
    U[Productor o técnico] --> W[React y Vite]
    W --> A[FastAPI: identidad y permisos]
    A --> H[Instantánea de hechos y contexto]
    H --> D[Hallazgos documentales]
    D --> M1[Mamdani 1: conservación]
    M1 --> M2[Mamdani 2: decisión]
    D --> M2
    K[Conocimiento versionado] --> D
    K --> M1
    K --> M2
    M2 --> E[Acción y explicación]
    E --> A
    A --> P[(PostgreSQL)]
    A --> W
```

El banner es una ilustración conceptual; el diagrama representa el flujo implementado. **La API determina decisiones y permisos.** El navegador captura datos y presenta resultados.

| Capa | Implementación |
| --- | --- |
| Interfaz | React 19, TypeScript, Vite 8, Tailwind CSS 4, TanStack Router y Query |
| API | FastAPI, Pydantic, JWT y cliente frontend tipado |
| Razonamiento | Python, hechos documentales, lógica de tres estados y dos niveles Mamdani |
| Persistencia | PostgreSQL 16, SQLAlchemy 2, Alembic, historial y auditoría |
| Ejecución | Docker Compose y Nginx para servir la SPA y dirigir peticiones |

### Historial, vigencia y versiones

Corregir significa registrar una nueva observación o evaluación. La instantánea conserva procedencia, versión del conocimiento, datos efectivos y traza difusa. Las versiones antiguas permiten reproducir sus resultados.

Una evaluación histórica favorable no implica autorización actual. La vigencia se calcula con el reloj del servidor, las revisiones, las incidencias y los eventos posteriores. Una cuarentena no desaparece al cambiar un dato: requiere resolución competente y la reevaluación que corresponda.

Una inspección del almacén puede aportar **13 campos ambientales y de higiene** si fecha, revisión y eventos permiten reutilizarla. Las mediciones y hallazgos del grano permanecen por unidad. Un dato actual desconocido o inválido no recupera automáticamente una observación favorable antigua.

El conocimiento sigue el ciclo `PROPUESTA → ACTIVADA → SUPERADA`, o `PROPUESTA → DESCARTADA`. La simulación mide el impacto antes de activar. Quien propone no puede activar su propia versión: debe intervenir otra persona con el rol de ingeniería. Para una demo con una sola cuenta existe `POSCOSEGRAN_ADQUISICION_PERMITIR_AUTOACTIVACION=true`; esa excepción está prohibida en producción.

### Estructura

```text
POSCOSEGRAN-SI-DIFUSO/
├── README.md              Documentación central
├── src/                   Interfaz, captura y explicación visual
├── public/                Iconos y recursos de la aplicación
├── backend/
│   ├── src/poscosegran/    API, dominio, motor, servicios y permisos
│   ├── migrations/        Evolución del esquema PostgreSQL
│   ├── scripts/           Preparación y mantenimiento
│   ├── sql/               Roles y privilegios
│   └── tests/             Pruebas Python e integración
├── knowledge/             Semillas, catálogo e históricos reproducibles
├── docs/openapi.json      Contrato generado utilizado por el proyecto
├── tests/e2e/             Recorridos de navegador
├── scripts/               Inicio Docker, verificación y despliegue
├── deploy/                Configuración de Nginx
├── infra/terraform/       Infraestructura AWS opcional
└── .github/               Workflow y banner
```

Las pruebas, los históricos YAML, los scripts y el contrato OpenAPI se conservan porque participan en verificación, reproducción o despliegue. Los archivos de asistentes y la documentación narrativa sustituida quedan fuera del seguimiento; sus copias locales no forman parte del proyecto publicado.

## API y configuración

La API usa **`/api/v1`**. El contrato completo está en [docs/openapi.json](docs/openapi.json); `/documentacion` ofrece su vista interactiva cuando está habilitada.

| Área | Rutas relativas a `/api/v1` |
| --- | --- |
| Identidad e inicio | `/me`, `/inicio` |
| Recursos | `/almacenes`, `/lotes`, `/unidades` |
| Inspecciones | `/almacenes/{id}/inspeccion`, `/almacenes/{id}/inspecciones` |
| Evaluaciones | `/unidades/{id}/evaluaciones`, `/evaluaciones/{id}`, `/evaluaciones/{id}/explicacion` |
| Historial y vigencia | `/unidades/{id}/historial`, `/unidades/{id}/vigencia` |
| Captura | `/unidades/{id}/borrador` |
| Seguimiento | Controles, eventos, planes, dictámenes, admisiones e incidencias |
| Conocimiento | `/conocimiento`, `/adquisicion/versiones`, `/adquisicion/propuestas` |
| Asignaciones | `/administracion/asignaciones` |

Los comandos de creación usan `Idempotency-Key`; los cambios sujetos a revisión usan `If-Match`. El primer borrador usa `If-None-Match: *`. Los errores incluyen `codigo`, `mensaje`, `campos` e `id_solicitud`; `X-Id-Solicitud` permite correlacionarlos con los registros. Las listas usan `limite` y `cursor`.

| Archivo o variable | Uso |
| --- | --- |
| `.env.example`, `backend/.env.example` | Plantillas públicas |
| `backend/.env` | Conexiones y credenciales locales; excluido de Git |
| `.env.local` | Configuración local del frontend; excluida de Git |
| `VITE_AUTH_MODE`, `VITE_API_URL` | Acceso local o Supabase y base de API |
| `POSCOSEGRAN_BD_URL_APP` | Credencial de aplicación sin DDL |
| `POSCOSEGRAN_BD_URL_MIGRACIONES` | Credencial separada para migraciones |
| `POSCOSEGRAN_JWT_*` | Modo, algoritmos, emisor, audiencia y verificación |
| `POSCOSEGRAN_CORS_ORIGENES` | Orígenes explícitos permitidos |

Las variables `VITE_*` son públicas: no deben contener contraseñas SQL, secretos JWT ni claves `service_role`. Los roles se consultan en PostgreSQL tras validar la identidad; el navegador no puede concederse permisos. La API no crea tablas al arrancar. Las políticas RLS opcionales no sustituyen su capa de autorización.

## Verificación

El workflow [.github/workflows/ci.yml](.github/workflows/ci.yml) comprueba análisis estático, migraciones, Python con PostgreSQL, privilegios SQL, contrato generado, compilación y recorridos Playwright. Sus pruebas y rutas forman parte del proyecto.

Para reproducir la verificación integrada, usa una **base local de pruebas**, nunca una base productiva:

```powershell
$env:POSCOSEGRAN_BD_URL_PRUEBAS = 'postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran'
$env:POSCOSEGRAN_BD_URL_PRUEBAS_APP = 'postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran'
powershell -ExecutionPolicy Bypass -File scripts/verificar.ps1
```

`-SaltarE2E` omite navegador. `-SinBd` ejecuta una revisión parcial que no equivale al workflow completo. En CI, `POSCOSEGRAN_EXIGIR_BD=1` convierte en fallo la omisión de pruebas de integración por falta de PostgreSQL.

<details>
<summary><strong>Comprobaciones por componente</strong></summary>

Desde la raíz:

```powershell
pnpm.cmd lint
pnpm.cmd build
backend/.venv/Scripts/python.exe backend/scripts/exportar_contrato.py
pnpm.cmd api:types
pnpm.cmd typecheck
```

Desde `backend`, con el entorno preparado:

```powershell
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m alembic check

# Solo el algoritmo: no requiere iniciar la interfaz
.venv/Scripts/python.exe -m pytest tests/test_sistema_difuso.py tests/test_mamdani_multivariable.py tests/test_decision_mamdani.py -q
```

Con frontend y API disponibles:

```powershell
pnpm.cmd exec playwright install chromium
$env:E2E_BASE_URL = 'http://localhost:8080'
pnpm.cmd test:e2e
```

Usa `http://localhost:8443` con Vite. Playwright obtiene la contraseña local desde `backend/.env`. Sus artefactos van a `test-results/`, excluido de Git.

</details>

La comprobación focalizada ejecutada durante la revisión documental aprobó **69 pruebas**. Cubre pertenencias, agregación, centroides, transiciones, exclusiones críticas y compatibilidad histórica; no sustituye la suite completa con PostgreSQL ni una validación agronómica.

`exportar_contrato.py` actualiza `docs/openapi.json`, `src/campos.json` y `src/alcance-inspeccion.json`; `pnpm api:types` actualiza `src/api/contrato.ts`. Conserva estos archivos y revisa sus diferencias al cambiar los esquemas.

La semilla vigente está en `knowledge/difuso/`. Los YAML de la raíz de `knowledge/`, `historico_mamdani_3_1/`, `historico_mamdani_4_0/` y `casos_referencia.json` permiten reproducir versiones anteriores. No se sobrescriben para hacer coincidir resultados nuevos. Las 242 expectativas históricas corresponden a la base determinista; no miden precisión agronómica del modelo actual.

## Operación y despliegue

<details>
<summary><strong>Migraciones, identidades y respaldo</strong></summary>

Desde `backend`, con `POSCOSEGRAN_BD_URL_MIGRACIONES` configurada:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic check
```

Para aprovisionar identidades o asignaciones con la credencial autorizada:

```powershell
.venv/Scripts/python.exe scripts/administrar.py --usuario UUID_AUTH --nombre "Nombre" --rol PRODUCTOR --motivo "Alta autorizada"
.venv/Scripts/python.exe scripts/administrar.py --usuario UUID_TECNICO --rol TECNICO --lote UUID_LOTE --responsable UUID_ADMIN --motivo "Asignación autorizada"
```

Puede usarse `--almacen UUID_ALMACEN` en vez de lote. Una vez aprovisionados los roles, el administrador gestiona asignaciones desde Configuración. Se conserva auditoría.

Respaldo desde la raíz y restauración en una **base nueva**:

```powershell
docker compose exec -T bd pg_dump -U postgres -d poscosegran -Fc -f /tmp/poscosegran.dump
docker compose cp bd:/tmp/poscosegran.dump ./respaldo.dump
docker compose exec -T bd createdb -U postgres poscosegran_restaurada
docker compose exec -T bd pg_restore -U postgres -d poscosegran_restaurada --no-owner /tmp/poscosegran.dump
```

Roles y privilegios se aprovisionan aparte. Comprueba conteos, versión Alembic y una evaluación histórica antes de cambiar conexiones. Guarda los respaldos fuera del repositorio.

</details>

<details>
<summary><strong>Proveedor de identidad y entornos públicos</strong></summary>

La demo funciona con acceso local. Supabase real requiere aprovisionamiento y verificación; no se presenta como una conexión ya probada.

1. Crea proveedor, usuarios y URLs de retorno. Configura `VITE_AUTH_MODE=supabase`, `VITE_SUPABASE_URL` y la clave pública del frontend.
2. En el backend usa `POSCOSEGRAN_ENTORNO=produccion`, verificación `JWKS`, algoritmos compatibles, emisor exacto, audiencia y URL de claves. Deshabilita el acceso local.
3. Aprovisiona roles y esquema con `backend/sql/roles_privilegios.sql`, aplica migraciones y después `backend/sql/permisos_aplicacion.sql`.
4. Carga la semilla desde un proceso administrativo y aprovisiona los UUID con `administrar.py`. Los roles declarados por el token no otorgan acceso por sí solos.
5. Usa HTTPS, conexiones SQL con SSL y CORS explícito. Deshabilita la autoactivación de propuestas por su autor.

El despliegue AWS y su enlace de acceso están documentados en [Despliegue en AWS](#despliegue-en-aws). `render.yaml` conserva una alternativa declarativa para otro proveedor; no corresponde al alojamiento del enlace Amplify publicado. Comprueba costos y planes del proveedor al crear o modificar entornos.

Estados, variables privadas y credenciales de Terraform están excluidos de Git. El acceso local compartido de una demo no constituye autenticación de producción.

</details>

### Problemas frecuentes

| Situación | Comprobación |
| --- | --- |
| Docker no responde | Inicia Docker Desktop antes del script |
| `inicializar` está detenido | `Exited (0)` es correcto; otro código requiere revisar registros |
| No se puede evaluar | Revisa `/salud/bd`, migraciones y conocimiento activo |
| 401 | Renueva sesión y comprueba autenticación |
| 403 o recurso no visible | Revisa rol, propiedad y asignación |
| 409 o 412 | Actualiza datos y revisiones antes de reenviar |
| 422 | Corrige los campos indicados por la API |
| Un resultado anterior ya no autoriza | Consulta vigencia, eventos e incidencias actuales |
| Vida previa inferior al historial | Conserva el acumulado documentado de esa unidad |
| No puedes activar tu propuesta | Debe revisarla otro ingeniero; la excepción solo existe fuera de producción |

## Alcance y conclusiones

POSCOSEGRAN aplica dos niveles Mamdani para combinar mediciones de conservación con evidencia y contexto. Sus 23 reglas difusas, apoyadas en 52 reglas documentales, permiten obtener una de siete acciones y explicar las pertenencias, las reglas activadas y el centroide que la sustenta.

La implementación en Python separa el conocimiento del motor y conserva versiones, historial y trazas. Los datos necesarios que faltan impiden autorizar, y las condiciones críticas excluyen conclusiones incompatibles; las pruebas computacionales y los casos simulados ayudan a comprobar ese comportamiento.

El sistema es un prototipo académico para maíz chulpi. Las curvas, las interacciones y los cortes requieren revisión especializada y validación de campo; sus índices no representan probabilidades de inocuidad ni demuestran una reducción real de pérdidas, y no certifican ausencia de micotoxinas.

## Fundamento documental y equipo

El [catálogo de conocimiento](knowledge/difuso/catalogo.yaml) conserva los localizadores S01–S09: SENASA, FAO, Codex/FAO-OMS, Purdue Extension y NDSU Extension. Distingue criterios publicados, transferidos, mixtos y políticas del prototipo. Los criterios comerciales y su aplicabilidad al chulpi requieren confirmación técnica.

Antecedentes del problema y de la técnica: [Díaz-Valderrama et al. (2020)](https://doi.org/10.1371/journal.pone.0240857), [Zadeh (1965)](https://doi.org/10.1016/S0019-9958(65)90241-X) y [Mamdani y Assilian (1975)](https://doi.org/10.1016/S0020-7373(75)80002-2).

**Docente:** Rosa Delgadillo. **Integrantes:** Barrera Estrella, Fernando Anthony Steve; Durand Galindo, Josué Yamil; Fernandez Díaz, Malco Enrique Junior; Gutierrez Yachachin, José Emmanuel; Salas Echenique, Andre Israel. **Lima, 2026.**
