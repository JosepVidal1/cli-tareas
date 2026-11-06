import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from tareas.configuracion import Accion
from tareas.errores import TareasError


def planificar(accion: Accion, origen_override: Path | None = None) -> list[tuple[Path, Path]]:
    if accion.tipo not in {"mover", "renombrar", "resumir-pdf", "renombrar-por-contenido"}:
        raise TareasError(f"'{accion.tipo}' no es una acción de archivos.")

    origen = origen_override or Path(accion.origen or "").expanduser()
    if not origen.is_dir():
        raise FileNotFoundError(f"la carpeta de origen no existe: '{origen}'.")

    filtro = accion.filtro or {}
    extensiones = {extension.lower() for extension in filtro.get("extensiones", [])}
    patron = filtro.get("patron")
    fecha_limite = (
        datetime.now().timestamp() - timedelta(days=accion.mas_antiguo_que_dias).total_seconds()
        if accion.mas_antiguo_que_dias is not None
        else None
    )
    archivos = [
        archivo
        for archivo in sorted(origen.iterdir(), key=lambda item: item.name.casefold())
        if archivo.is_file()
        and (archivo.suffix.lower() in extensiones if extensiones else re.search(patron, archivo.name))
        and (fecha_limite is None or archivo.stat().st_mtime <= fecha_limite)
    ]

    if accion.tipo == "mover":
        destino = Path(accion.destino or "").expanduser()
        return [(archivo, destino / archivo.name) for archivo in archivos]
    if accion.tipo in {"resumir-pdf", "renombrar-por-contenido"}:
        return [(archivo, archivo) for archivo in archivos]

    cambios: list[tuple[Path, Path]] = []
    for numero, archivo in enumerate(archivos, start=1):
        fecha = datetime.fromtimestamp(archivo.stat().st_mtime)
        nombre = (accion.plantilla or "").format(fecha=fecha, n=numero, ext=archivo.suffix)
        cambios.append((archivo, archivo.with_name(nombre)))
    return cambios


def validar_destinos(cambios: list[tuple[Path, Path]]) -> None:
    destinos: set[str] = set()
    for origen, destino in cambios:
        clave = str(destino).casefold()
        if clave in destinos:
            raise TareasError(f"varios archivos producirían el mismo destino: '{destino}'.")
        destinos.add(clave)
        if destino.exists() and destino != origen:
            raise FileExistsError(f"el destino ya existe; no se sobrescribe: '{destino}'.")


def ejecutar_archivos(
    accion: Accion,
    simular: bool = False,
    origen_override: Path | None = None,
) -> list[tuple[Path, Path]]:
    cambios = planificar(accion, origen_override)
    validar_destinos(cambios)
    if simular or not cambios:
        return cambios

    completados: list[tuple[Path, Path]] = []
    try:
        for origen, destino in cambios:
            if origen == destino:
                continue
            if accion.tipo == "mover":
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(origen), str(destino))
            else:
                origen.rename(destino)
            completados.append((origen, destino))
    except OSError as error:
        fallos_reversion: list[str] = []
        for origen, destino in reversed(completados):
            try:
                if accion.tipo == "mover":
                    origen.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(destino), str(origen))
                else:
                    destino.rename(origen)
            except OSError as error_reversion:
                fallos_reversion.append(f"'{destino}' -> '{origen}': {error_reversion}")
        if fallos_reversion:
            detalle = "; ".join(fallos_reversion)
            raise TareasError(
                f"falló la operación ({error}) y no se pudieron revertir todos los cambios: {detalle}."
            ) from error
        raise TareasError(
            f"falló la operación ({error}); se revirtieron los cambios anteriores del lote."
        ) from error
    return cambios
