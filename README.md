# tareas

`tareas` es una CLI para organizar archivos mediante acciones declaradas en
`acciones.json`. Puede mover y renombrar archivos, ejecutar secuencias y usar un
proveedor de IA compatible con la API de chat de OpenAI para resumir o proponer
nombres de PDFs.

Las acciones de archivos no borran ni sobrescriben. Prueba primero con
`--simular` y utiliza una carpeta de pruebas, no tus archivos personales.

## Requisitos e instalación

Se necesita Python 3.12 o posterior y [uv](https://docs.astral.sh/uv/).

Para desarrollar o probar el proyecto:

```bash
uv sync --dev
uv run tareas --help
```

Para instalar la herramienta desde el repositorio público:

```bash
uv tool install git+https://github.com/JosepVidal1/cli-tareas
```

También se puede instalar con `pipx`:

```bash
pipx install git+https://github.com/JosepVidal1/cli-tareas
```

El comando `tareas` queda disponible en el `PATH`. La configuración se lee por
defecto de `./acciones.json`; si trabajas desde otra carpeta, indica la ruta
explícitamente con `--config`.

## Órdenes

```text
tareas --help
tareas version
tareas listar [CARPETA] [--json]
tareas acciones
tareas validar
tareas ejecutar NOMBRE [CARPETA] [--simular] [--si]
tareas --config RUTA acciones
```

Ejemplos:

```bash
tareas version
tareas listar ~/pruebas-tareas --json
tareas --config ./acciones.json validar
tareas ejecutar ordenar-descargas --simular
tareas ejecutar limpieza-semanal --simular
```

`--simular` muestra los cambios de archivos sin aplicarlos. Las acciones de IA
requieren confirmar que se envíe el texto del PDF al proveedor; esto también se
aplica al ejecutar una acción IA con `--simular`, porque la simulación no evita
la llamada al modelo. `--si` da esa confirmación sin preguntar, para
automatización. En el caso de
`renombrar-por-contenido`, `--simular` es obligatorio y solo se muestran
propuestas: nunca renombra por sí misma. Los destinos existentes se rechazan,
nunca se sobrescriben.

Los códigos de salida son `0` si todo va bien, `1` si falla la ejecución, `2`
si la acción no existe y `3` si la configuración es inválida.

## Acciones incluidas

Las rutas de ejemplo están bajo `~/pruebas-tareas`. Crea allí las carpetas
necesarias y algunos archivos de prueba antes de ejecutar acciones sin
`--simular`.

| Acción | Qué hace |
| --- | --- |
| `ordenar-descargas` | Mueve `.pdf` y `.docx` a `Documentos/PDF`. |
| `recoger-capturas` | Mueve capturas PNG con el patrón configurado. |
| `renombrar-fotos` | Usa fecha de modificación, secuencia y extensión original. |
| `ordenar-imagenes` | Mueve imágenes descargadas a `Pictures/Descargadas`. |
| `ordenar-instaladores` | Mueve instaladores a `Downloads/Instaladores`. |
| `limpieza-semanal` | Ejecuta en orden las cuatro acciones de organización anteriores. |
| `resumir-pdf` | Extrae texto de apuntes PDF y genera un resumen Markdown mediante IA. |
| `renombrar-por-contenido` | Sugiere nombres para PDFs mediante IA; solo muestra propuestas. |

La aplicación no implementa borrado de archivos. Las acciones de IA solo envían
el texto extraído de los PDFs seleccionados después de pedir confirmación. Se
envían como máximo los primeros 30.000 caracteres de cada documento.

## Configuración de IA y secretos

La integración usa una API compatible con `POST /chat/completions`. Copia
`.env.example` a `.env` y configura la clave, la URL base y el modelo indicados
por tu proveedor:

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

No escribas claves en el código, `acciones.json`, el README, los prompts ni el
chat. `.env` está excluido por `.gitignore`; no lo añadas a Git. Si la clave
falta o el proveedor no responde, la orden de IA explica el problema sin
traceback; `--help`, `acciones`, `validar` y las acciones sin IA siguen
disponibles. No se realizan llamadas de red en las pruebas.

## Formato de `acciones.json`

El fichero es un objeto JSON con `version: 1` y una lista `acciones`. Cada
acción de archivos necesita `nombre`, `descripcion`, `tipo`, `origen` y
`filtro`. El filtro acepta `extensiones` o `patron` (expresión regular).

Ejemplo:

```json
{
  "version": 1,
  "acciones": [
    {
      "nombre": "ordenar-pdf",
      "descripcion": "Mueve PDFs a una carpeta",
      "tipo": "mover",
      "origen": "~/pruebas-tareas/entrada",
      "filtro": {
        "extensiones": [".pdf"]
      },
      "destino": "~/pruebas-tareas/salida"
    }
  ]
}
```

`mover` requiere `destino`. `renombrar` requiere `plantilla`, que puede usar
`{fecha:FORMATO}`, `{n:FORMATO}` y `{ext}`. `secuencia` requiere una lista de
nombres en `acciones`; las referencias se validan y no pueden formar ciclos.
Las acciones IA (`resumir-pdf` y `renombrar-por-contenido`) solo aceptan PDFs.
El programa valida el JSON antes de ejecutar y señala el campo inválido.

## Desarrollo y pruebas

Las pruebas usan exclusivamente `tmp_path` de pytest; no operan sobre tus
archivos ni hacen peticiones de red:

```bash
uv run pytest -q
```

GitHub Actions ejecuta la misma suite en Ubuntu, Windows y macOS para Python
3.12 en cada `push` y `pull_request`.

## Estructura

- `src/tareas/cli.py`: interfaz Typer y códigos de salida.
- `src/tareas/configuracion.py`: carga y validación de `acciones.json`.
- `src/tareas/motor.py`: ejecución de acciones y secuencias.
- `src/tareas/acciones.py`: planificación y cambios seguros de archivos.
- `src/tareas/proveedor_ia.py`: cliente de API compatible con chat.
- `tests/`: pruebas automáticas sin red ni archivos reales.
- `docs/adr/`: decisiones de diseño.
- `CHANGELOG.md`: cambios previstos y condición para la versión 1.0.
