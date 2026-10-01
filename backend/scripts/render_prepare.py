"""Prepara PostgreSQL en Render antes de iniciar la API.

Aplica migraciones en cada despliegue y carga el conocimiento de ejemplo solo si
la base todavía no tiene una versión activa. No restablece versiones ya aprobadas.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa

from poscosegran.config import Configuracion, obtener_configuracion
from poscosegran.db.modelos import VersionConocimiento

BACKEND = Path(__file__).resolve().parents[1]


def main() -> int:
    configuracion = obtener_configuracion()
    entorno = os.environ.copy()
    url_migraciones = str(Configuracion.normalizar_url_postgres(
        entorno.get("POSCOSEGRAN_BD_URL_MIGRACIONES") or configuracion.bd_url_app
    ))
    entorno["POSCOSEGRAN_BD_URL_MIGRACIONES"] = url_migraciones
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=entorno,
        check=True,
    )

    motor = sa.create_engine(url_migraciones, pool_pre_ping=True)
    try:
        with motor.connect() as conexion:
            hay_version_activa = conexion.scalar(
                sa.select(VersionConocimiento.id)
                .where(VersionConocimiento.activa.is_(True))
                .limit(1)
            )
        if hay_version_activa is None:
            carpeta = Path(os.environ.get("POSCOSEGRAN_KNOWLEDGE", "/knowledge"))
            # El cargador usa la conexión de aplicación: solo este proceso de
            # preparación recibe privilegios de migración para la semilla.
            entorno["POSCOSEGRAN_BD_URL_APP"] = url_migraciones
            subprocess.run(
                [sys.executable, "-m", "poscosegran.conocimiento.cargar", str(carpeta),
                 "--activar", "--notas", "Carga inicial de despliegue"],
                cwd=BACKEND, env=entorno, check=True,
            )
        else:
            print("Base de conocimiento activa encontrada; se conserva sin cambios.")
    finally:
        motor.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
