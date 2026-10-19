# POSCOSEGRAN

Sistema de inferencia difusa Mamdani para evaluar la autorización de almacenamiento de maíz chulpi. React + Vite, FastAPI, motor Python y PostgreSQL 16. La interfaz consume la API real; las decisiones, permisos e incidencias se calculan en el servidor.


**Modelo vigente:** base 5.0, motor `3.0.0-mamdani`. El primer nivel tiene **4 mediciones** (3 aplicables en hermético), **9 reglas** y una salida de conservación. El nivel final combina **11 antecedentes derivados o de contexto**, **14 reglas Mamdani** y entrega una de **7 decisiones**. Son **23 reglas difusas** en total; el catálogo conserva 52 reglas documentales y 94 campos de medición, verificación y gestión. Las condiciones críticas se excluyen de conclusiones permisivas mediante los antecedentes de las reglas. El centroide final codifica acciones, no probabilidades de inocuidad.

El núcleo para revisar con la profesora está en [`sistema_difuso/decision.py`](backend/src/poscosegran/sistema_difuso/decision.py) y [`sistema_difuso/motor.py`](backend/src/poscosegran/sistema_difuso/motor.py); las curvas en [`pertenencia.py`](backend/src/poscosegran/sistema_difuso/pertenencia.py), la agregación y el centroide exacto en [`defuzzificacion.py`](backend/src/poscosegran/sistema_difuso/defuzzificacion.py). Las variables, curvas, reglas finales MF01–MF14 y clasificación se versionan en [`knowledge/difuso/base_conocimiento.yaml`](knowledge/difuso/base_conocimiento.yaml), sección `difuso.decision`.

Consulta [el modelo final y su cobertura](docs/CONVERSION_DIFUSA.md) y [su verificación](docs/VERIFICACION_MAMDANI_FINAL.md). La implementación histórica se conserva para reproducir resultados previos. La decisión nueva se obtiene del centroide final; los límites y hallazgos documentales alimentan sus antecedentes.

## Ejecutar todo con Docker

Solo requiere Docker Desktop. Desde la raíz:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/iniciar_docker.ps1
```

El script genera secretos locales si todavía no existe `backend/.env`, construye las imágenes, prepara PostgreSQL mediante un contenedor efímero y levanta frontend y backend. Abre [la aplicación Docker](http://localhost:8080). La salud de la API queda en [localhost:8080/salud/bd](http://localhost:8080/salud/bd) y su documentación en [localhost:8080/documentacion](http://localhost:8080/documentacion).

Para detenerlo sin borrar los datos:

```powershell
docker compose --env-file backend/.env down
```

## Ejecutar en desarrollo local

Requisitos: Docker Desktop iniciado, Python 3.13, Node.js 22 y pnpm. Desde la raíz:

```powershell
docker compose up -d bd
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
pnpm.cmd install --frozen-lockfile
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
```

Si usas uv: `uv venv backend/.venv --python 3.13` y `uv pip install --python backend/.venv/Scripts/python.exe -e "backend[dev]"`. No recrees el entorno si ya existe.

El preparador aplica migraciones, carga la base Mamdani 5.0 y crea cuatro usuarios de desarrollo: `productor`, `tecnico`, `administrador` e `ingeniero` (ingeniería del conocimiento, para el módulo de adquisición). La contraseña vigente es `POSCOSEGRAN_AUTH_LOCAL_PASSWORD` en `backend/.env`; no se sobrescribe si ya existe. El alias `testeo` corresponde a PRODUCTOR. Esta credencial se limita al entorno local.

En dos terminales:

```powershell
cd backend
.venv/Scripts/python.exe -m uvicorn poscosegran.api.app:crear_app --factory --reload --host 127.0.0.1 --port 8000
```

```powershell
pnpm.cmd dev
```

Abre [la aplicación local](http://localhost:8443). API interactiva: [documentación local](http://127.0.0.1:8000/documentacion). El técnico necesita una asignación al lote o almacén para ver sus unidades; el administrador no obtiene acceso general a datos de producción. El ingeniero del conocimiento mantiene la base desde *Adquisición* y tampoco ve unidades.

> Activar una versión de conocimiento exige **cuatro ojos**: quien la propuso no puede activarla. Para recorrer el ciclo completo con la única cuenta `ingeniero` de desarrollo, añade `POSCOSEGRAN_ADQUISICION_PERMITIR_AUTOACTIVACION=true` a `backend/.env`. La configuración rechaza esa opción si el entorno es `produccion`.

## Verificar antes de subir

```powershell
$env:POSCOSEGRAN_BD_URL_PRUEBAS = 'postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran'
$env:POSCOSEGRAN_BD_URL_PRUEBAS_APP = 'postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran'
powershell -ExecutionPolicy Bypass -File scripts/verificar.ps1
```

Reproduce los gates del workflow en el mismo orden y se detiene en el primero que falle. Añade `-SaltarE2E` para omitir Playwright, o `-SinBd` para una verificación parcial que avisa de que no equivale al CI. No contiene credenciales: las lee del entorno.

## Documentación

- [Instalación, contenedores, Supabase y respaldos](docs/INSTALACION_DESPLIEGUE.md)
- [Manual de uso](docs/MANUAL_USUARIO.md)
- [Arquitectura e integración](docs/ARQUITECTURA.md)
- [API y contrato generado](docs/API.md)
- [Pruebas y límites de la verificación](docs/PRUEBAS.md)
- [Decisiones de implementación](docs/DECISIONES.md)
- [Base de conocimiento vigente](knowledge/POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md)

Supabase todavía no está configurado. El acceso local permite recorrer la aplicación sin ese servicio y está bloqueado en producción. Este prototipo orienta sobre almacenamiento; no certifica inocuidad ni ausencia de micotoxinas.
