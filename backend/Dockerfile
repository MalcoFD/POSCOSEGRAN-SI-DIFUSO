FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/pyproject.toml ./
RUN python -c "import pathlib,tomllib; p=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); pathlib.Path('/tmp/poscosegran-requirements.txt').write_text('\n'.join(p['project']['dependencies'])+'\n')"
RUN --mount=type=cache,target=/root/.cache/pip pip install -r /tmp/poscosegran-requirements.txt 'setuptools>=75' wheel
COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps --no-build-isolation .
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
COPY knowledge/*.yaml /knowledge/
COPY knowledge/casos_referencia.json /knowledge/
COPY knowledge/difuso/*.yaml /knowledge/difuso/
# Semilla de la base de conocimiento y casos de referencia del módulo de adquisición.
ENV POSCOSEGRAN_KNOWLEDGE=/knowledge

RUN useradd --create-home --uid 10001 aplicacion && chown -R aplicacion:aplicacion /app
USER aplicacion

EXPOSE 8000
CMD ["uvicorn", "poscosegran.api.app:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
