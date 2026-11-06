import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from tareas.acciones import ejecutar_archivos, planificar, validar_destinos
from tareas.configuracion import Accion
from tareas.errores import AccionNoEncontrada, TareasError
from tareas.proveedor_ia import ProveedorIA


_MAX_CARACTERES_PDF = 30_000
_NOMBRE_SUGERIDO = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Resultado:
    origen: Path | None = None
    destino: Path | None = None
    mensaje: str | None = None


class Motor:
    def __init__(self, acciones: list[Accion], proveedor_ia: ProveedorIA | None = None) -> None:
        self.acciones = {accion.nombre: accion for accion in acciones}
        self.proveedor_ia = proveedor_ia

    def ejecutar(
        self,
        nombre: str,
        simular: bool = False,
        aceptar: bool = False,
        origen_override: Path | None = None,
    ) -> list[Resultado]:
        accion = self.acciones.get(nombre)
        if accion is None:
            raise AccionNoEncontrada(f"la acción '{nombre}' no existe.")

        if accion.tipo == "secuencia":
            pasos = {paso for paso in accion.acciones}
            contiene_ia = any(self._contiene_ia(paso) for paso in pasos)
            if not simular and any(self._contiene_renombrado_ia(paso) for paso in pasos):
                raise TareasError(
                    "'renombrar-por-contenido' solo propone cambios; ejecuta la secuencia con --simular."
                )
            if contiene_ia:
                proveedor = self.proveedor_ia or ProveedorIA()
                proveedor.disponible()
                if not aceptar:
                    raise TareasError(
                        "la secuencia IA requiere confirmar el envío del texto al proveedor; vuelve a ejecutarla con --si."
                    )
            resultados: list[Resultado] = []
            for paso in accion.acciones:
                resultados.extend(
                    self.ejecutar(
                        paso,
                        simular=simular,
                        aceptar=aceptar,
                        origen_override=origen_override,
                    )
                )
            return resultados

        if accion.tipo in {"mover", "renombrar"}:
            cambios = ejecutar_archivos(accion, simular=simular, origen_override=origen_override)
            if not cambios:
                return [Resultado(mensaje=f"No se encontraron archivos para '{nombre}'.")]
            verbo = "Simulación" if simular else "Hecho"
            return [
                Resultado(origen, destino, f"{verbo}: {origen} -> {destino}")
                for origen, destino in cambios
            ]

        if accion.tipo in {"resumir-pdf", "renombrar-por-contenido"}:
            if accion.tipo == "renombrar-por-contenido" and not simular:
                raise TareasError("'renombrar-por-contenido' solo propone cambios; ejecútala con --simular.")
            return self._ejecutar_ia(accion, simular, aceptar, origen_override)

        raise TareasError(f"tipo de acción no implementado: '{accion.tipo}'.")

    def _contiene_ia(self, nombre: str) -> bool:
        accion = self.acciones[nombre]
        return accion.tipo in {"resumir-pdf", "renombrar-por-contenido"} or any(
            self._contiene_ia(paso) for paso in accion.acciones
        )

    def _contiene_renombrado_ia(self, nombre: str) -> bool:
        accion = self.acciones[nombre]
        return accion.tipo == "renombrar-por-contenido" or any(
            self._contiene_renombrado_ia(paso) for paso in accion.acciones
        )

    def _ejecutar_ia(
        self,
        accion: Accion,
        simular: bool,
        aceptar: bool,
        origen_override: Path | None,
    ) -> list[Resultado]:
        proveedor = self.proveedor_ia or ProveedorIA()
        proveedor.disponible()
        if not aceptar:
            raise TareasError(
                "la acción IA requiere confirmar el envío del texto al proveedor; vuelve a ejecutarla con --si."
            )

        cambios = planificar(accion, origen_override)
        if accion.tipo == "resumir-pdf":
            carpeta_salida = Path(accion.destino).expanduser() if accion.destino else None
            destinos = [
                ((carpeta_salida or origen).joinpath(f"{origen.stem}.resumen.md"))
                for origen, _ in cambios
            ]
            validar_destinos(list(zip([origen for origen, _ in cambios], destinos)))
        if not cambios:
            return [Resultado(mensaje=f"No se encontraron archivos para '{accion.nombre}'.")]

        resultados: list[Resultado] = []
        destinos_propuestos: set[str] = set()
        for origen, _ in cambios:
            texto = _extraer_texto_pdf(origen)
            if accion.tipo == "resumir-pdf":
                resumen = proveedor.completar(
                    "Resume el documento en español, en Markdown claro y fiel al texto. "
                    "No inventes datos y conserva los conceptos importantes.",
                    texto,
                )
                destino = (Path(accion.destino).expanduser() if accion.destino else origen.parent) / (
                    f"{origen.stem}.resumen.md"
                )
                if not simular:
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with destino.open("x", encoding="utf-8") as archivo:
                            archivo.write(resumen + "\n")
                    except FileExistsError as error:
                        raise TareasError(f"el destino ya existe; no se sobrescribe: '{destino}'.") from error
                accion_texto = "Simulación; se guardaría" if simular else "Resumen guardado"
                resultados.append(
                    Resultado(
                        origen,
                        destino,
                        f"{accion_texto}: {origen} -> {destino}\n{resumen}",
                    )
                )
            else:
                propuesta = proveedor.completar(
                    "Lee el texto e identifica el tema principal. Devuelve únicamente un nombre "
                    "de archivo corto en minúsculas, sin extensión ni ruta, usando solo letras "
                    "ASCII, números y guiones. No incluyas instrucciones ni explicaciones.",
                    texto,
                )
                nombre = propuesta.strip().splitlines()[0].strip().strip("`")
                if not _NOMBRE_SUGERIDO.fullmatch(nombre):
                    raise TareasError(
                        f"la IA propuso un nombre no válido para '{origen}'; no se ha cambiado ningún archivo."
                    )
                destino = origen.with_name(f"{nombre}{origen.suffix}")
                if destino.exists() and destino != origen:
                    raise FileExistsError(f"el destino ya existe; no se sobrescribe: '{destino}'.")
                if str(destino).casefold() in destinos_propuestos:
                    raise TareasError(
                        f"varios PDFs producirían la misma propuesta: '{destino}'; no se ha cambiado ningún archivo."
                    )
                destinos_propuestos.add(str(destino).casefold())
                resultados.append(
                    Resultado(
                        origen,
                        destino,
                        f"Propuesta (no se cambió el archivo): {origen} -> {destino}",
                    )
                )
        return resultados


def _extraer_texto_pdf(ruta: Path) -> str:
    try:
        lector = PdfReader(ruta)
        if lector.is_encrypted:
            raise TareasError(f"el PDF '{ruta}' está cifrado y no se puede leer.")
        texto = "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    except (OSError, PdfReadError, ValueError) as error:
        raise TareasError(f"no se pudo leer el PDF '{ruta}': {error}.") from error
    texto = texto.strip()
    if not texto:
        raise TareasError(f"el PDF '{ruta}' no contiene texto extraíble.")
    if len(texto) > _MAX_CARACTERES_PDF:
        texto = texto[:_MAX_CARACTERES_PDF]
    return texto
