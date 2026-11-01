import json
import os
import sys
import tempfile
from pathlib import Path

import typer

from tareas.acciones import Accion, _validar_accion, cargar_acciones, ejecutar_accion


_COMANDO_ANADIR_ACCION = "añadir-accion"


def _anadir_accion(ruta_configuracion: Path) -> None:
    typer.echo(
        "Puedes dejar campos vacíos; si falta un campo obligatorio para la acción, "
        "no se guardará."
    )
    valores = {
        campo: typer.prompt(etiqueta, default="", show_default=False).strip()
        for campo, etiqueta in (
            ("nombre", "Nombre"),
            ("descripcion", "Descripción"),
            ("tipo", "Tipo (mover o renombrar)"),
            ("origen", "Carpeta de origen"),
            ("filtro_entrada", "Filtro (.pdf,.docx o patron:^expresion$)"),
            ("destino", "Carpeta de destino"),
            ("plantilla", "Plantilla para renombrar"),
        )
    }

    nueva_accion = {
        campo: valores[campo]
        for campo in ("nombre", "descripcion", "tipo", "origen", "destino", "plantilla")
        if valores[campo]
    }
    filtro_entrada = valores["filtro_entrada"]
    if filtro_entrada.startswith("patron:"):
        nueva_accion["filtro"] = {"patron": filtro_entrada.removeprefix("patron:")}
    elif filtro_entrada:
        nueva_accion["filtro"] = {
            "extensiones": [extension.strip() for extension in filtro_entrada.split(",")]
        }

    configuracion = json.loads(ruta_configuracion.read_text(encoding="utf-8"))
    acciones_existentes = cargar_acciones(ruta_configuracion)
    nombres = {accion.nombre for accion in acciones_existentes}
    nombres.add(_COMANDO_ANADIR_ACCION)
    _validar_accion(nueva_accion, "nueva acción", nombres)

    configuracion["acciones"].append(nueva_accion)
    temporal: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ruta_configuracion.parent,
            prefix=f".{ruta_configuracion.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            json.dump(configuracion, archivo, indent=2, ensure_ascii=False)
            archivo.write("\n")
        os.replace(temporal, ruta_configuracion)
        temporal = None
    finally:
        if temporal is not None:
            try:
                temporal.unlink()
            except FileNotFoundError:
                pass

    typer.echo(f"Acción '{nueva_accion['nombre']}' añadida correctamente.")


def _crear_comando_anadir_accion(ruta_configuracion: Path):
    def comando() -> None:
        try:
            _anadir_accion(ruta_configuracion)
        except (OSError, ValueError) as error:
            typer.echo(f"Error al añadir la acción: {error}", err=True)
            raise typer.Exit(code=1) from error

    comando.__name__ = "anadir_accion"
    return comando


def _crear_comando(accion: Accion):
    def comando(
        simular: bool = typer.Option(
            False,
            "--simular",
            help="Muestra los cambios sin modificar archivos.",
        ),
    ) -> None:
        try:
            ejecutar_accion(accion, simular=simular)
        except (OSError, ValueError) as error:
            typer.echo(f"Error al ejecutar '{accion.nombre}': {error}", err=True)
            raise typer.Exit(code=1) from error

    comando.__name__ = f"accion_{accion.nombre.replace('-', '_')}"
    return comando


def crear_app(
    acciones: list[Accion],
    ruta_configuracion: Path | None = None,
) -> typer.Typer:
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help="""Ejecuta acciones definidas en acciones.json.

Para crear un comando, añade un objeto a la lista "acciones" de ese archivo:

{
  "nombre": "ordenar-pdf",
  "descripcion": "Mueve los PDF a una carpeta",
  "tipo": "mover",
  "origen": "~/Downloads",
  "filtro": {"extensiones": [".pdf"]},
  "destino": "~/Documents/PDF"
}

Cada acción necesita nombre, descripcion, tipo, origen y filtro. El filtro
debe indicar "extensiones" o un "patron" (expresión regular). El tipo "mover"
requiere "destino"; el tipo "renombrar" requiere "plantilla", que puede usar
{fecha:FORMATO}, {n:FORMATO} y {ext}. Ejecuta "tareas NOMBRE --simular"
para comprobar los cambios sin modificar archivos. Ejecuta
"tareas añadir-accion" para crear una acción de forma interactiva.""",
    )

    @app.callback()
    def _callback() -> None:
        pass

    if ruta_configuracion is None:
        ruta_configuracion = Path.cwd() / "acciones.json"
        if not ruta_configuracion.is_file():
            ruta_configuracion = Path(__file__).resolve().parents[2] / "acciones.json"
    if any(accion.nombre == _COMANDO_ANADIR_ACCION for accion in acciones):
        raise ValueError(f"'{_COMANDO_ANADIR_ACCION}' es un nombre reservado.")
    app.command(
        name=_COMANDO_ANADIR_ACCION,
        help="Crea una acción nueva de forma interactiva.",
    )(_crear_comando_anadir_accion(ruta_configuracion))
    for accion in acciones:
        app.command(name=accion.nombre, help=accion.descripcion)(_crear_comando(accion))
    return app


def main() -> None:
    ruta_configuracion = Path.cwd() / "acciones.json"
    if not ruta_configuracion.is_file():
        ruta_configuracion = Path(__file__).resolve().parents[2] / "acciones.json"

    try:
        acciones = cargar_acciones(ruta_configuracion)
    except (OSError, ValueError) as error:
        typer.echo(f"Error al cargar '{ruta_configuracion}': {error}", err=True)
        raise typer.Exit(code=2) from error

    nombres = {accion.nombre for accion in acciones}
    argumentos = sys.argv[1:]
    if argumentos and not argumentos[0].startswith("-") and argumentos[0] not in nombres | {
        _COMANDO_ANADIR_ACCION
    }:
        typer.echo(f"Error: la acción '{argumentos[0]}' no existe.", err=True)
        raise typer.Exit(code=2)

    if _COMANDO_ANADIR_ACCION in nombres:
        typer.echo(f"Error: '{_COMANDO_ANADIR_ACCION}' es un nombre reservado.", err=True)
        raise typer.Exit(code=2)

    crear_app(acciones, ruta_configuracion)()


__all__ = ["crear_app", "main"]
