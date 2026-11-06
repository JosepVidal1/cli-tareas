import json
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Optional

import typer
from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from rich.table import Table

from tareas.configuracion import Accion, cargar_acciones
from tareas.errores import AccionNoEncontrada, ConfigError, TareasError
from tareas.motor import Motor
from tareas.proveedor_ia import ProveedorIA


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="CLI para automatizar tareas de archivos definidas en acciones.json.",
)


@app.callback()
def _configurar(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Usa otro archivo de configuración JSON.",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


def _ruta_configuracion(ctx: typer.Context) -> Path:
    indicada = ctx.obj.get("config")
    if indicada is not None:
        return indicada.expanduser()
    local = Path.cwd() / "acciones.json"
    if local.is_file():
        return local
    return Path(__file__).resolve().parents[2] / "acciones.json"


def _cargar(ctx: typer.Context) -> list[Accion]:
    try:
        return cargar_acciones(_ruta_configuracion(ctx))
    except ConfigError as error:
        typer.echo(f"Error de configuración: {error}", err=True)
        raise typer.Exit(code=error.codigo_salida) from error


def _mostrar_error(error: Exception) -> None:
    if isinstance(error, TareasError):
        codigo = error.codigo_salida
    else:
        codigo = 1
    typer.echo(f"Error: {error}", err=True)
    raise typer.Exit(code=codigo) from error


def _contiene_accion_ia(nombre: str, acciones: dict[str, Accion]) -> bool:
    accion = acciones[nombre]
    if accion.tipo in {"resumir-pdf", "renombrar-por-contenido"}:
        return True
    return any(_contiene_accion_ia(paso, acciones) for paso in accion.acciones)


def _contiene_propuesta_ia(nombre: str, acciones: dict[str, Accion]) -> bool:
    accion = acciones[nombre]
    if accion.tipo == "renombrar-por-contenido":
        return True
    return any(_contiene_propuesta_ia(paso, acciones) for paso in accion.acciones)


@app.command("version")
def version_comando() -> None:
    """Muestra la versión instalada."""
    try:
        instalada = version("tareas")
    except PackageNotFoundError:
        instalada = "0.1.0"
    typer.echo(instalada)


@app.command("acciones")
def listar_acciones(ctx: typer.Context) -> None:
    """Lista las acciones definidas en la configuración."""
    acciones = _cargar(ctx)
    tabla = Table(title="Acciones disponibles")
    tabla.add_column("Nombre", style="cyan")
    tabla.add_column("Tipo")
    tabla.add_column("Descripción")
    for accion in acciones:
        tabla.add_row(accion.nombre, accion.tipo, accion.descripcion)
    Console(file=sys.stdout).print(tabla)


@app.command("validar")
def validar_configuracion(ctx: typer.Context) -> None:
    """Valida acciones.json e indica el campo que falla."""
    ruta = _ruta_configuracion(ctx)
    _cargar(ctx)
    typer.echo(f"Configuración válida: {ruta}")


@app.command("listar")
def listar_archivos(
    carpeta: Optional[Path] = typer.Argument(None, help="Carpeta que se mostrará (por defecto, la actual)."),
    json_salida: bool = typer.Option(False, "--json", help="Devuelve una lista JSON sin formato visual."),
) -> None:
    """Lista nombre, tipo, tamaño y fecha de los archivos de una carpeta."""
    ruta = (carpeta or Path.cwd()).expanduser()
    try:
        if not ruta.is_dir():
            raise FileNotFoundError(f"la carpeta no existe: '{ruta}'.")
        registros = []
        for archivo in sorted(ruta.iterdir(), key=lambda item: item.name.casefold()):
            if not archivo.is_file():
                continue
            info = archivo.stat()
            registros.append(
                {
                    "nombre": archivo.name,
                    "tipo": archivo.suffix.lower() or "sin extensión",
                    "tamano_bytes": info.st_size,
                    "modificado": datetime.fromtimestamp(info.st_mtime).astimezone().isoformat(
                        timespec="seconds"
                    ),
                }
            )
    except OSError as error:
        _mostrar_error(error)

    if json_salida:
        typer.echo(json.dumps(registros, ensure_ascii=False, indent=2))
        return
    tabla = Table(title=f"Archivos en {ruta}")
    tabla.add_column("Nombre")
    tabla.add_column("Tipo")
    tabla.add_column("Tamaño (bytes)", justify="right")
    tabla.add_column("Modificado")
    for registro in registros:
        tabla.add_row(
            registro["nombre"],
            registro["tipo"],
            str(registro["tamano_bytes"]),
            registro["modificado"],
        )
    Console(file=sys.stdout).print(tabla)


@app.command("ejecutar")
def ejecutar_accion(
    ctx: typer.Context,
    nombre: str = typer.Argument(..., help="Nombre de una acción de acciones.json."),
    carpeta: Optional[Path] = typer.Argument(None, help="Carpeta de origen alternativa."),
    simular: bool = typer.Option(False, "--simular", help="Muestra los cambios sin modificar archivos."),
    si: bool = typer.Option(False, "--si", help="Confirma el envío del texto a IA y la escritura de resultados."),
) -> None:
    """Ejecuta una acción configurada."""
    acciones = _cargar(ctx)
    por_nombre = {accion.nombre: accion for accion in acciones}
    accion = por_nombre.get(nombre)
    if accion is None:
        _mostrar_error(AccionNoEncontrada(f"la acción '{nombre}' no existe."))

    if _contiene_propuesta_ia(nombre, por_nombre) and not simular:
        _mostrar_error(
            TareasError("la acción solo propone cambios; ejecútala con --simular.")
        )

    proveedor = None
    aceptar = si
    if _contiene_accion_ia(nombre, por_nombre):
        load_dotenv(find_dotenv(usecwd=True))
        proveedor = ProveedorIA()
        try:
            proveedor.disponible()
        except TareasError as error:
            _mostrar_error(error)
        if not aceptar:
            aceptar = typer.confirm(
                "El contenido del PDF se enviará al proveedor de IA. ¿Continuar?",
                default=False,
            )
            if not aceptar:
                typer.echo("Cancelado; no se ha enviado ningún contenido.")
                return

    motor = Motor(acciones, proveedor_ia=proveedor)
    try:
        resultados = motor.ejecutar(
            nombre,
            simular=simular,
            aceptar=aceptar,
            origen_override=carpeta.expanduser() if carpeta else None,
        )
    except (TareasError, OSError, ValueError) as error:
        _mostrar_error(error)
    for resultado in resultados:
        if resultado.mensaje:
            typer.echo(resultado.mensaje)


__all__ = ["app"]
