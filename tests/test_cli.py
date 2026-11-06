import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tareas.cli import app


runner = CliRunner()


def _config(ruta: Path, origen: Path, destino: Path) -> Path:
    ruta.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "ordenar-pdf",
                        "descripcion": "Mueve PDFs",
                        "tipo": "mover",
                        "origen": str(origen),
                        "filtro": {"extensiones": [".pdf"]},
                        "destino": str(destino),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return ruta


def test_cli_validar_y_ejecutar_con_config_alternativa(tmp_path: Path) -> None:
    origen = tmp_path / "entrada"
    destino = tmp_path / "salida"
    origen.mkdir()
    (origen / "apuntes.pdf").write_text("apuntes", encoding="utf-8")
    configuracion = _config(tmp_path / "acciones.json", origen, destino)

    valido = runner.invoke(app, ["--config", str(configuracion), "validar"])
    simulado = runner.invoke(
        app,
        ["--config", str(configuracion), "ejecutar", "ordenar-pdf", "--simular"],
    )
    assert (origen / "apuntes.pdf").exists()
    ejecutado = runner.invoke(app, ["--config", str(configuracion), "ejecutar", "ordenar-pdf"])

    assert valido.exit_code == 0
    assert "Configuración válida" in valido.stdout
    assert simulado.exit_code == 0
    assert "Simulación:" in simulado.stdout
    assert ejecutado.exit_code == 0
    assert (destino / "apuntes.pdf").read_text(encoding="utf-8") == "apuntes"


def test_accion_ia_sin_clave_no_afecta_acciones_normales(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("TAREAS_AI_API_KEY", raising=False)
    monkeypatch.setattr("tareas.cli.load_dotenv", lambda _: False)
    origen = tmp_path / "entrada"
    destino = tmp_path / "salida"
    origen.mkdir()
    (origen / "apuntes.pdf").write_text("contenido", encoding="utf-8")
    configuracion = tmp_path / "acciones.json"
    configuracion.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "ordenar-pdf",
                        "descripcion": "Mueve PDFs",
                        "tipo": "mover",
                        "origen": str(origen),
                        "filtro": {"extensiones": [".pdf"]},
                        "destino": str(destino),
                    },
                    {
                        "nombre": "resumir-pdf",
                        "descripcion": "Resume PDFs",
                        "tipo": "resumir-pdf",
                        "origen": str(origen),
                        "filtro": {"extensiones": [".pdf"]},
                    },
                    {
                        "nombre": "secuencia-ia",
                        "descripcion": "Prueba de secuencia",
                        "tipo": "secuencia",
                        "acciones": ["resumir-pdf"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    acciones = runner.invoke(app, ["--config", str(configuracion), "acciones"])
    resumen = runner.invoke(
        app,
        ["--config", str(configuracion), "ejecutar", "resumir-pdf", "--simular", "--si"],
    )
    secuencia = runner.invoke(
        app,
        ["--config", str(configuracion), "ejecutar", "secuencia-ia", "--simular"],
    )
    mover = runner.invoke(
        app,
        ["--config", str(configuracion), "ejecutar", "ordenar-pdf", "--simular"],
    )

    assert acciones.exit_code == 0
    assert "resumir-pdf" in acciones.stdout
    assert resumen.exit_code == 1
    assert "IA no disponible" in resumen.stderr
    assert "Traceback" not in resumen.output
    assert secuencia.exit_code == 1
    assert "IA no disponible" in secuencia.stderr
    assert mover.exit_code == 0
    assert "Simulación:" in mover.stdout


def test_cli_devuelve_codigo_3_y_mensaje_para_json_invalido(tmp_path: Path) -> None:
    configuracion = tmp_path / "acciones.json"
    configuracion.write_text("{", encoding="utf-8")

    resultado = runner.invoke(app, ["--config", str(configuracion), "validar"])

    assert resultado.exit_code == 3
    assert "JSON no válido" in resultado.stderr
    assert "Traceback" not in resultado.output


def test_cli_ayuda_y_listado_json(tmp_path: Path) -> None:
    (tmp_path / "informe final.txt").write_text("texto", encoding="utf-8")
    ayuda = runner.invoke(app, ["--help"])
    listado = runner.invoke(app, ["listar", str(tmp_path), "--json"])

    assert ayuda.exit_code == 0
    assert "ejecutar" in ayuda.stdout
    assert listado.exit_code == 0
    assert json.loads(listado.stdout)[0]["nombre"] == "informe final.txt"


def test_accion_desconocida_devuelve_codigo_2(tmp_path: Path) -> None:
    origen = tmp_path / "entrada"
    origen.mkdir()
    configuracion = _config(tmp_path / "acciones.json", origen, tmp_path / "salida")

    resultado = runner.invoke(
        app,
        ["--config", str(configuracion), "ejecutar", "no-existe"],
    )

    assert resultado.exit_code == 2
    assert "la acción 'no-existe' no existe" in resultado.stderr
    assert "Traceback" not in resultado.output
