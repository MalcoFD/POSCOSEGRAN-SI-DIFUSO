# POSCOSEGRAN

Sistema académico de apoyo a la gestión del almacenamiento poscosecha de maíz chulpi. Implementa un solo nivel Mamdani tipo 1 y conserva la relación entre observaciones, cálculo e historial.

La base **6.0**, parámetros **2.0** y motor **4.0.0-matricial** publica dos matrices alternativas:

| Modalidad | Entradas | Reglas |
|---|---|---|
| No hermético | Humedad, temperatura, HR del almacén y estado físico/sanitario | 256 = 4×4×4×4 |
| Hermético | Humedad, temperatura y estado físico/sanitario | 64 = 4×4×4 |

Las mediciones continuas tienen cuatro etiquetas solapadas. La inspección es categórica con pertenencias características 0/1: sin hallazgos, daño físico, indicios biológicos y hallazgo crítico. No se inventa un porcentaje de contaminación. Moho visible o insectos vivos observados requieren la categoría crítica, con evidencia. La modalidad hermética exige barrera íntegra y procedimiento interno documentado; HR exterior no interviene.

El flujo es captura → validación → fuzzificación → matriz → mínimo de antecedentes → recorte mínimo → agregación máxima → centroide exacto → interpretación e historial. La salida es un índice de intervención y una de cinco recomendaciones. Los datos pendientes se guardan sin índice. Las fechas, permisos, revisiones y la vigencia son controles de la aplicación, no otra base de recomendaciones.

## Desarrollo local

Requiere Python 3.13, Node.js 22, pnpm y Docker Desktop iniciado. Reutilice los entornos existentes.

```powershell
docker compose up -d bd
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
pnpm.cmd install --frozen-lockfile
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
```

API desde `backend`:

```powershell
.venv/Scripts/python.exe -m uvicorn poscosegran.api.app:crear_app --factory --reload --host 127.0.0.1 --port 8000
```

Frontend desde la raíz:

```powershell
pnpm.cmd dev
```

Aplicación: http://localhost:8443. La configuración del frontend debe usar `VITE_AUTH_MODE=local`. Usuarios: `productor` o `testeo`, `tecnico`, `administrador`, `ingeniero` y `revisor`. La contraseña está en `POSCOSEGRAN_AUTH_LOCAL_PASSWORD` de `backend/.env`; en una instalación nueva el preparador usa `testeo`. Los archivos de configuración existentes se conservan. El técnico requiere asignación a los recursos. Administrador e ingeniero tienen funciones distintas del productor.

Como alternativa, `scripts/iniciar_docker.ps1` prepara la aplicación completa en http://localhost:8080. El volumen PostgreSQL conserva el historial. Para detener utilice `docker compose down` sin eliminar volúmenes.

## Uso y cuatro corridas

Registre almacén, lote y unidad. En Evaluar complete tres pasos: lote/modalidad, mediciones e inspección. Registre fecha y método de las mediciones; la humedad exige INSTRUMENTAL o LABORATORIO. La inspección necesita evidencia. El modelo admite observaciones de hasta 168 horas por política de demostración, sin fechas futuras. Un desconocido no se sustituye por cero.

| Lote de demostración | Datos principales | Índice | Recomendación |
|---|---|---:|---|
| M320-L01 | Hermético; H12 %, T10 °C, sin hallazgos | 4,666667 | Autorizar almacenamiento |
| M320-L02 | No hermético; H12 %, T18 °C, HR50 %, sin hallazgos | 19,165217 | Autorizar con monitoreo |
| M320-L03 | No hermético; H13,5 %, T25 °C, HR60 %, sin hallazgos | 81 | Suspender almacenamiento |
| M320-L04 | No hermético; H12 %, T10 °C, HR50 %, hallazgo crítico | 97,666667 | Separar y revisar técnicamente |

Con la API local iniciada, `backend/scripts/registrar_corridas_4.py` registra esos lotes mediante HTTP y verifica cuatro evaluaciones y su auditoría. Si ya existen, consulta sus historiales sin duplicarlos. Son datos simulados; la guía indica cómo repetirlos con otros códigos y fechas actuales. La evidencia local está en `docs/EVIDENCIA_CORRIDAS_4.json`.

Una evaluación favorable puede tener autorización invalidada por una incidencia abierta o un evento posterior. La recomendación histórica no cambia. Se necesita resolver técnicamente la incidencia y reevaluar. La recomendación no certifica inocuidad, duración segura ni ausencia de micotoxinas.

## Modelo y comprobaciones

- `knowledge/base_conocimiento.yaml`: matrices, funciones, operadores y política ejecutables.
- `knowledge/catalogo.yaml`: las mismas 320 reglas descritas y nueve referencias.
- `knowledge/matriz_320.json`: exportación del modelo para revisión.
- `knowledge/casos_referencia.json`: 320 anclas congeladas para comparar versiones.
- `knowledge/corridas_4.json`: entradas, trazas y resultados esperados de los cuatro escenarios.
- `backend/scripts/generar_modelo_matricial.py`: generación editorial de las reglas, fuera de cada evaluación.
- `backend/scripts/auditar_superficie.py`: diagnóstico reproducible de la superficie continua.

Las fuentes SENASA, FAO, Codex y Purdue orientan referencias y precauciones. Las curvas, interacciones y cortes son diseño del prototipo, pendiente de calibración para chulpi. La malla examinada no presenta descensos de categoría, pero sí oscilaciones locales del centroide. Consulte el informe para sus límites.

```powershell
pnpm.cmd typecheck
pnpm.cmd lint
pnpm.cmd build
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
pnpm.cmd test:e2e
```

Las pruebas marcadas `bd` requieren PostgreSQL migrado en `POSCOSEGRAN_BD_URL_PRUEBAS`. Con `POSCOSEGRAN_EXIGIR_BD=1`, su ausencia detiene la suite. Use una base de pruebas distinta de la demostración. No se sustituye PostgreSQL por SQLite. `ruff check`, `mypy` y `alembic check` completan las comprobaciones del backend.

## Documentación

- [Reglas actuales](docs/REGLAS_ACTUALES.md): entradas, funciones, las 320 reglas en matrices, cálculo, recomendaciones, fuentes y límites.
- [Resumen del cambio](docs/RESUMEN_CAMBIOS_MAMDANI_320.md): integración, limpieza, pruebas y preparación para despliegue.
- [Contrato OpenAPI](docs/openapi.json).

Los informes Word, la guía de cuatro lotes, las evidencias y el material de clase permanecen en la carpeta local `docs`, excluidos de Git. El equipo distribuye los informes por separado. La actualización de diapositivas queda a su cargo.

## Despliegue

La configuración AWS existente permanece en `infra/terraform` y `scripts/desplegar_aws.ps1`. La revisión matricial se verificó localmente. El despliegue remoto necesita publicar esta versión, ejecutar la migración 0008 y cargar un identificador de conocimiento nuevo en la base de destino. Un entorno que ya tenga otra base 6.0 con distinto contenido no debe sobrescribirla: debe publicarse otra versión. No se borran ni recalculan evaluaciones históricas.
