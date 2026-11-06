import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tareas.errores import AccionNoValida, ConfigError


_TIPOS_ARCHIVO = {"mover", "renombrar"}
_TIPOS_IA = {"resumir-pdf", "renombrar-por-contenido"}
_TIPOS = _TIPOS_ARCHIVO | _TIPOS_IA | {"secuencia"}
_NOMBRE_VALIDO = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Accion:
    nombre: str
    descripcion: str
    tipo: str
    origen: str | None = None
    filtro: dict[str, Any] | None = None
    destino: str | None = None
    plantilla: str | None = None
    acciones: tuple[str, ...] = ()
    mas_antiguo_que_dias: int | None = None


def cargar_acciones(ruta: Path) -> list[Accion]:
    try:
        with ruta.open(encoding="utf-8") as archivo:
            configuracion = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ConfigError(f"JSON no válido en '{ruta}': {error.msg} (línea {error.lineno}).") from error
    except UnicodeDecodeError as error:
        raise ConfigError(f"'{ruta}' no contiene texto UTF-8 válido.") from error
    except OSError as error:
        raise ConfigError(f"no se puede leer '{ruta}': {error.strerror or error}.") from error

    if not isinstance(configuracion, dict) or not isinstance(configuracion.get("acciones"), list):
        raise ConfigError("el archivo debe contener una lista 'acciones'.")
    if type(configuracion.get("version")) is not int or configuracion["version"] != 1:
        raise ConfigError("el campo 'version' debe ser el número 1.")

    acciones: list[Accion] = []
    nombres: set[str] = set()
    for indice, datos in enumerate(configuracion["acciones"], start=1):
        accion = _validar_accion(datos, f"acciones[{indice - 1}]", nombres)
        acciones.append(accion)
        nombres.add(accion.nombre)

    _validar_referencias(acciones)
    return acciones


def _validar_accion(datos: Any, prefijo: str, nombres: set[str]) -> Accion:
    if not isinstance(datos, dict):
        raise AccionNoValida(f"{prefijo}: se esperaba un objeto.")

    nombre = _texto(datos, "nombre", prefijo)
    descripcion = _texto(datos, "descripcion", prefijo)
    tipo = _texto(datos, "tipo", prefijo)
    if not _NOMBRE_VALIDO.fullmatch(nombre):
        raise AccionNoValida(f"{prefijo}.nombre: usa minúsculas, números y guiones.")
    if nombre in nombres:
        raise AccionNoValida(f"{prefijo}.nombre: '{nombre}' está duplicado.")
    if tipo not in _TIPOS:
        raise AccionNoValida(f"{prefijo}.tipo: '{tipo}' no está soportado.")

    if tipo == "secuencia":
        nombres_acciones = datos.get("acciones")
        if (
            not isinstance(nombres_acciones, list)
            or not nombres_acciones
            or not all(isinstance(item, str) and item for item in nombres_acciones)
        ):
            raise AccionNoValida(f"{prefijo}.acciones: debe ser una lista no vacía de nombres.")
        return Accion(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            acciones=tuple(nombres_acciones),
        )

    origen = _texto(datos, "origen", prefijo)
    filtro = datos.get("filtro")
    if not isinstance(filtro, dict):
        raise AccionNoValida(f"{prefijo}.filtro: debe ser un objeto.")

    extensiones = filtro.get("extensiones")
    patron = filtro.get("patron")
    edad = filtro.get("mas_antiguo_que_dias")
    if extensiones is not None and (
        not isinstance(extensiones, list)
        or not extensiones
        or not all(isinstance(extension, str) and extension.startswith(".") for extension in extensiones)
    ):
        raise AccionNoValida(f"{prefijo}.filtro.extensiones: debe ser una lista de extensiones como '.pdf'.")
    if patron is not None:
        if not isinstance(patron, str):
            raise AccionNoValida(f"{prefijo}.filtro.patron: debe ser texto.")
        try:
            re.compile(patron)
        except re.error as error:
            raise AccionNoValida(f"{prefijo}.filtro.patron: expresión regular no válida: {error}.") from error
    if extensiones is None and patron is None:
        raise AccionNoValida(f"{prefijo}.filtro: indica 'extensiones' o 'patron'.")
    if edad is not None and (type(edad) is not int or edad < 1):
        raise AccionNoValida(f"{prefijo}.filtro.mas_antiguo_que_dias: debe ser un entero positivo.")

    destino = datos.get("destino")
    plantilla = datos.get("plantilla")
    if tipo == "mover":
        if not isinstance(destino, str) or not destino.strip():
            raise AccionNoValida(f"{prefijo}.destino: es obligatorio para una acción 'mover'.")
    elif tipo == "renombrar":
        if not isinstance(plantilla, str) or not plantilla:
            raise AccionNoValida(f"{prefijo}.plantilla: es obligatoria para una acción 'renombrar'.")
        try:
            plantilla.format(fecha=datetime.now(), n=1, ext=".pdf")
        except (IndexError, KeyError, ValueError) as error:
            raise AccionNoValida(f"{prefijo}.plantilla: formato no válido: {error}.") from error
    elif tipo in _TIPOS_IA:
        if tipo == "renombrar-por-contenido" and not (
            extensiones is not None and {item.lower() for item in extensiones} == {".pdf"}
        ):
            raise AccionNoValida(
                f"{prefijo}.filtro.extensiones: 'renombrar-por-contenido' solo admite archivos PDF."
            )
        if tipo == "resumir-pdf" and not (
            extensiones is not None and {item.lower() for item in extensiones} == {".pdf"}
        ):
            raise AccionNoValida(f"{prefijo}.filtro.extensiones: 'resumir-pdf' solo admite archivos PDF.")
        if destino is not None and (not isinstance(destino, str) or not destino.strip()):
            raise AccionNoValida(f"{prefijo}.destino: debe ser texto no vacío.")

    return Accion(
        nombre=nombre,
        descripcion=descripcion,
        tipo=tipo,
        origen=origen,
        filtro=filtro,
        destino=destino,
        plantilla=plantilla,
        mas_antiguo_que_dias=edad,
    )


def _texto(datos: dict[str, Any], campo: str, prefijo: str) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise AccionNoValida(f"{prefijo}.{campo}: debe ser texto no vacío.")
    return valor


def _validar_referencias(acciones: list[Accion]) -> None:
    por_nombre = {accion.nombre: accion for accion in acciones}
    for accion in acciones:
        for nombre in accion.acciones:
            if nombre not in por_nombre:
                raise AccionNoValida(
                    f"acciones.{accion.nombre}.acciones: no existe la acción '{nombre}'."
                )
            if nombre == accion.nombre:
                raise AccionNoValida(f"acciones.{accion.nombre}.acciones: no puede incluirse a sí misma.")

    visitadas: set[str] = set()
    en_curso: set[str] = set()

    def visitar(nombre: str) -> None:
        if nombre in en_curso:
            raise AccionNoValida(f"acciones.{nombre}.acciones: se ha detectado una secuencia circular.")
        if nombre in visitadas:
            return
        en_curso.add(nombre)
        for dependiente in por_nombre[nombre].acciones:
            visitar(dependiente)
        en_curso.remove(nombre)
        visitadas.add(nombre)

    for accion in acciones:
        visitar(accion.nombre)
