import json
from pathlib import Path
from urllib.error import URLError

import pytest

from tareas import acciones as modulo_acciones
from tareas.acciones import ejecutar_archivos
from tareas.configuracion import Accion, cargar_acciones
from tareas.errores import AccionNoValida, ConfigError, IAUnavailableError, TareasError
from tareas.motor import Motor
from tareas.proveedor_ia import ProveedorIA


def _accion_mover(origen: Path, destino: Path) -> Accion:
    return Accion(
        nombre="mover-pdf",
        descripcion="Mueve PDFs",
        tipo="mover",
        origen=str(origen),
        filtro={"extensiones": [".pdf"]},
        destino=str(destino),
    )


def test_mover_simula_y_ejecuta_sin_tocar_otros_archivos(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    pdf = origen / "apuntes.pdf"
    otro = origen / "foto.png"
    pdf.write_text("contenido", encoding="utf-8")
    otro.write_text("imagen", encoding="utf-8")
    accion = _accion_mover(origen, destino)

    cambios = ejecutar_archivos(accion, simular=True)
    assert cambios == [(pdf, destino / "apuntes.pdf")]
    assert pdf.read_text(encoding="utf-8") == "contenido"
    assert not destino.exists()

    ejecutar_archivos(accion)
    assert not pdf.exists()
    assert (destino / "apuntes.pdf").read_text(encoding="utf-8") == "contenido"
    assert otro.read_text(encoding="utf-8") == "imagen"


def test_no_mueve_si_el_destino_ya_existe(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    destino.mkdir()
    archivo = origen / "apuntes.pdf"
    archivo.write_text("original", encoding="utf-8")
    (destino / archivo.name).write_text("no sobrescribir", encoding="utf-8")

    with pytest.raises(FileExistsError, match="no se sobrescribe"):
        ejecutar_archivos(_accion_mover(origen, destino))

    assert archivo.read_text(encoding="utf-8") == "original"
    assert (destino / archivo.name).read_text(encoding="utf-8") == "no sobrescribir"


def test_carga_json_roto_indica_linea_y_campo(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_text('{"version": 1, "acciones": [}', encoding="utf-8")

    with pytest.raises(ConfigError, match="JSON no válido.*línea 1"):
        cargar_acciones(ruta)


def test_configuracion_debe_usar_utf8(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_bytes(b'{"version": 1, "acciones": []}\xff')

    with pytest.raises(ConfigError, match="UTF-8 válido"):
        cargar_acciones(ruta)


def test_validacion_identifica_campo_invalido(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "mover-pdf",
                        "descripcion": "Mueve PDFs",
                        "tipo": "mover",
                        "origen": "~/entrada",
                        "filtro": {"patron": "["},
                        "destino": "~/salida",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AccionNoValida, match=r"acciones\[0\]\.filtro\.patron"):
        cargar_acciones(ruta)


def test_ruta_de_origen_inexistente_da_error_controlado(tmp_path: Path) -> None:
    accion = _accion_mover(tmp_path / "no-existe", tmp_path / "destino")

    with pytest.raises(FileNotFoundError, match="carpeta de origen no existe"):
        ejecutar_archivos(accion, simular=True)


def test_accion_ia_sin_clave_falla_sin_hacer_peticion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAREAS_AI_API_KEY", raising=False)
    proveedor = ProveedorIA(api_key="", base_url="https://example.invalid/v1", modelo="test")

    with pytest.raises(IAUnavailableError, match="siguen disponibles"):
        proveedor.completar("resumen", "texto de prueba")


def test_proveedor_usa_api_compatible_sin_conectar_a_la_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RespuestaFalsa:
        def __enter__(self) -> "RespuestaFalsa":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "respuesta de prueba"}}]}).encode()

    def urlopen_falso(solicitud, timeout: int) -> RespuestaFalsa:
        assert solicitud.full_url == "https://modelo.example/v1/chat/completions"
        assert solicitud.get_header("Authorization") == "Bearer clave-de-prueba"
        assert timeout == 30
        cuerpo = json.loads(solicitud.data)
        assert cuerpo["model"] == "modelo-prueba"
        assert cuerpo["messages"][1]["content"] == "texto de prueba"
        return RespuestaFalsa()

    monkeypatch.setattr("tareas.proveedor_ia.urlopen", urlopen_falso)
    proveedor = ProveedorIA(
        api_key="clave-de-prueba",
        base_url="https://modelo.example/v1",
        modelo="modelo-prueba",
    )

    assert proveedor.completar("instrucciones", "texto de prueba") == "respuesta de prueba"


def test_fallo_de_red_se_convierte_en_error_humano(monkeypatch: pytest.MonkeyPatch) -> None:
    def urlopen_sin_red(solicitud, timeout: int) -> None:
        raise URLError("red desconectada")

    monkeypatch.setattr("tareas.proveedor_ia.urlopen", urlopen_sin_red)
    proveedor = ProveedorIA(
        api_key="clave-de-prueba",
        base_url="https://modelo.example/v1",
        modelo="modelo-prueba",
    )

    with pytest.raises(IAUnavailableError, match="comprueba la red"):
        proveedor.completar("instrucciones", "texto de prueba")


def test_secuencia_circular_es_rechazada(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "primera",
                        "descripcion": "Primera",
                        "tipo": "secuencia",
                        "acciones": ["segunda"],
                    },
                    {
                        "nombre": "segunda",
                        "descripcion": "Segunda",
                        "tipo": "secuencia",
                        "acciones": ["primera"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AccionNoValida, match="secuencia circular"):
        cargar_acciones(ruta)


def test_ia_propone_nombre_sin_renombrar(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    origen = tmp_path / "apuntes.pdf"
    origen.write_bytes(b"contenido pdf simulado")
    accion = Accion(
        nombre="renombrar-por-contenido",
        descripcion="Propone un nombre",
        tipo="renombrar-por-contenido",
        origen=str(tmp_path),
        filtro={"extensiones": [".pdf"]},
    )

    class ProveedorFalso(ProveedorIA):
        def disponible(self) -> None:
            return None

        def completar(self, instrucciones: str, contenido: str) -> str:
            assert contenido == "apuntes de matemáticas"
            return "apuntes-de-matematicas"

    monkeypatch.setattr("tareas.motor._extraer_texto_pdf", lambda ruta: "apuntes de matemáticas")
    motor = Motor([accion], proveedor_ia=ProveedorFalso(api_key="test"))

    resultado = motor.ejecutar("renombrar-por-contenido", simular=True, aceptar=True)

    assert "apuntes-de-matematicas.pdf" in resultado[0].mensaje
    assert origen.exists()
    assert not (tmp_path / "apuntes-de-matematicas.pdf").exists()


def test_ia_genera_resumen_markdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    origen = tmp_path / "apuntes.pdf"
    origen.write_bytes(b"contenido pdf simulado")
    carpeta_salida = tmp_path / "resumenes"
    accion = Accion(
        nombre="resumir-pdf",
        descripcion="Resume apuntes",
        tipo="resumir-pdf",
        origen=str(tmp_path),
        filtro={"extensiones": [".pdf"]},
        destino=str(carpeta_salida),
    )

    class ProveedorFalso(ProveedorIA):
        def completar(self, instrucciones: str, contenido: str) -> str:
            assert contenido == "contenido académico"
            return "# Resumen\n\nIdeas principales."

    monkeypatch.setattr("tareas.motor._extraer_texto_pdf", lambda ruta: "contenido académico")
    motor = Motor([accion], proveedor_ia=ProveedorFalso(api_key="test"))

    resultados = motor.ejecutar("resumir-pdf", aceptar=True)

    assert resultados[0].destino == carpeta_salida / "apuntes.resumen.md"
    assert (carpeta_salida / "apuntes.resumen.md").read_text(encoding="utf-8") == (
        "# Resumen\n\nIdeas principales.\n"
    )


def test_accion_ia_no_permite_renombrar_sin_simular(tmp_path: Path) -> None:
    accion = Accion(
        nombre="renombrar-por-contenido",
        descripcion="Propone un nombre",
        tipo="renombrar-por-contenido",
        origen=str(tmp_path),
        filtro={"extensiones": [".pdf"]},
    )
    motor = Motor([accion], proveedor_ia=ProveedorIA(api_key="test"))

    with pytest.raises(TareasError, match="solo propone cambios"):
        motor.ejecutar("renombrar-por-contenido", simular=False, aceptar=True)


def test_fallo_a_mitad_de_un_lote_revierte_los_movimientos(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    (origen / "a.pdf").write_text("a", encoding="utf-8")
    (origen / "b.pdf").write_text("b", encoding="utf-8")
    mover_real = modulo_acciones.shutil.move
    llamadas = 0

    def mover_con_fallo(origen_archivo: str, destino_archivo: str) -> str:
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise OSError("fallo simulado")
        return mover_real(origen_archivo, destino_archivo)

    monkeypatch.setattr("tareas.acciones.shutil.move", mover_con_fallo)

    with pytest.raises(TareasError, match="se revirtieron los cambios"):
        ejecutar_archivos(_accion_mover(origen, destino))

    assert (origen / "a.pdf").read_text(encoding="utf-8") == "a"
    assert (origen / "b.pdf").read_text(encoding="utf-8") == "b"
    assert not (destino / "a.pdf").exists()
