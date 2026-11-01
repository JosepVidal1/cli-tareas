import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Accion:
    nombre: str
    descripcion: str
    tipo: str
    origen: str
    filtro: dict[str, Any]
    destino: str | None = None
    plantilla: str | None = None


def cargar_acciones(ruta: Path) -> list[Accion]:
    with ruta.open(encoding="utf-8") as archivo:
        configuracion = json.load(archivo)

    if not isinstance(configuracion, dict) or not isinstance(configuracion.get("acciones"), list):
        raise ValueError("el archivo debe contener una lista 'acciones'.")
    if configuracion.get("version") != 1:
        raise ValueError("la versión de configuración debe ser 1.")

    acciones: list[Accion] = []
    nombres: set[str] = set()
    for indice, datos in enumerate(configuracion["acciones"], start=1):
        accion = _validar_accion(datos, f"acción {indice}", nombres)
        acciones.append(accion)
        nombres.add(accion.nombre)

    return acciones


def _validar_accion(datos: Any, prefijo: str, nombres: set[str]) -> Accion:
    if not isinstance(datos, dict):
        raise ValueError(f"{prefijo}: se esperaba un objeto.")

    nombre = _texto(datos, "nombre", prefijo)
    descripcion = _texto(datos, "descripcion", prefijo)
    tipo = _texto(datos, "tipo", prefijo)
    origen = _texto(datos, "origen", prefijo)
    filtro = datos.get("filtro")
    if not isinstance(filtro, dict):
        raise ValueError(f"{prefijo}: 'filtro' debe ser un objeto.")

    extensiones = filtro.get("extensiones")
    patron = filtro.get("patron")
    if extensiones is not None and (
        not isinstance(extensiones, list)
        or not all(isinstance(extension, str) and extension for extension in extensiones)
    ):
        raise ValueError(f"{prefijo}: 'filtro.extensiones' debe ser una lista de texto.")
    if patron is not None:
        if not isinstance(patron, str):
            raise ValueError(f"{prefijo}: 'filtro.patron' debe ser texto.")
        try:
            re.compile(patron)
        except re.error as error:
            raise ValueError(f"{prefijo}: patrón no válido: {error}") from error
    if extensiones is None and patron is None:
        raise ValueError(f"{prefijo}: el filtro debe indicar 'extensiones' o 'patron'.")

    if nombre in nombres:
        raise ValueError(f"nombre de acción duplicado: '{nombre}'.")
    if nombre.startswith("-") or not nombre.strip():
        raise ValueError(f"{prefijo}: nombre de acción no válido.")

    destino = datos.get("destino")
    plantilla = datos.get("plantilla")
    if tipo == "mover":
        if not isinstance(destino, str) or not destino:
            raise ValueError(f"{prefijo}: la acción 'mover' requiere 'destino'.")
    elif tipo == "renombrar":
        if not isinstance(plantilla, str) or not plantilla:
            raise ValueError(f"{prefijo}: la acción 'renombrar' requiere 'plantilla'.")
    else:
        raise ValueError(f"{prefijo}: tipo de acción no soportado: '{tipo}'.")

    return Accion(
        nombre=nombre,
        descripcion=descripcion,
        tipo=tipo,
        origen=origen,
        filtro=filtro,
        destino=destino,
        plantilla=plantilla,
    )


def _texto(datos: dict[str, Any], campo: str, prefijo: str) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{prefijo}: '{campo}' debe ser texto no vacío.")
    return valor


def _archivos_coincidentes(accion: Accion) -> list[Path]:
    origen = Path(accion.origen).expanduser()
    if not origen.is_dir():
        raise FileNotFoundError(f"la carpeta de origen no existe: '{origen}'.")

    extensiones = {extension.lower() for extension in accion.filtro.get("extensiones", [])}
    patron = accion.filtro.get("patron")
    return [
        archivo
        for archivo in sorted(origen.iterdir())
        if archivo.is_file()
        and (
            archivo.suffix.lower() in extensiones
            if extensiones
            else re.search(patron, archivo.name) is not None
        )
    ]


def _planificar(accion: Accion) -> list[tuple[Path, Path]]:
    archivos = _archivos_coincidentes(accion)
    if accion.tipo == "mover":
        destino = Path(accion.destino or "").expanduser()
        return [(archivo, destino / archivo.name) for archivo in archivos]

    cambios: list[tuple[Path, Path]] = []
    for numero, archivo in enumerate(archivos, start=1):
        fecha = datetime.fromtimestamp(archivo.stat().st_mtime)
        nombre = (accion.plantilla or "").format(
            fecha=fecha,
            n=numero,
            ext=archivo.suffix,
        )
        cambios.append((archivo, archivo.with_name(nombre)))
    return cambios


def ejecutar_accion(accion: Accion, simular: bool = False) -> None:
    cambios = _planificar(accion)
    destinos: set[Path] = set()
    for origen, destino in cambios:
        if destino in destinos:
            raise ValueError(f"varios archivos producirían el mismo destino: '{destino}'.")
        destinos.add(destino)
        if destino.exists() and destino != origen:
            raise FileExistsError(f"el destino ya existe: '{destino}'.")

    if not cambios:
        print("No se encontraron archivos que coincidan.")
        return

    for origen, destino in cambios:
        etiqueta = "Simulación" if simular else "Procesando"
        print(f"{etiqueta}: {origen} -> {destino}")
        if simular:
            continue
        if accion.tipo == "mover":
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origen), str(destino))
        elif destino != origen:
            origen.rename(destino)
