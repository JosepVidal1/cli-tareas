# tareas

`tareas` es una aplicación de línea de comandos para automatizar tareas sencillas
con archivos: moverlos entre carpetas o renombrarlos según una plantilla. Las
acciones se configuran en `acciones.json`, por lo que se pueden adaptar las rutas
y los filtros sin modificar el código del programa.

El programa procesa archivos de una carpeta cada vez. Antes de ejecutar una
acción sobre archivos reales, se recomienda probarla con `--simular`.

## Requisitos e instalación

- Python 3.12 o posterior.
- [uv](https://docs.astral.sh/uv/), para instalar y ejecutar el proyecto.

Desde la carpeta del proyecto:

```bash
uv sync
```

Puedes ejecutar los comandos con `uv run tareas`:

```bash
uv run tareas --help
```

## Ayuda y uso

La ayuda general muestra las acciones disponibles y una breve descripción de cada
una:

```bash
tareas --help
```

Para consultar las opciones de un comando concreto:

```bash
tareas ordenar-descargas --help
```

La forma general de ejecutar una acción es:

```bash
tareas <nombre-de-acción> [--simular]
```

Por ejemplo:

```bash
tareas ordenar-descargas --simular
tareas ordenar-descargas
```

`--simular` muestra los cambios que se harían sin modificar archivos. Sin esa
opción, los archivos coincidentes se procesan realmente. Si no hay coincidencias,
el programa lo indica. Si la carpeta de origen no existe, el destino ya existe o
se produce otro error de ejecución, se muestra un error y el comando termina con
código distinto de cero.

También se puede crear una acción de forma interactiva:

```bash
tareas añadir-accion
```

El asistente solicita el nombre, la descripción, el tipo, la carpeta de origen,
el filtro y el destino o la plantilla que correspondan. La nueva acción se añade
a `acciones.json`. Los campos obligatorios deben completarse para poder guardarla.

## Acciones configuradas

Las acciones se cargan desde `acciones.json`. En la configuración actual están
disponibles:

| Acción | Descripción | Tipo y archivos |
| --- | --- | --- |
| `ordenar-descargas` | Mueve archivos de Descargas a Documentos/PDF. | Mover archivos `.pdf` y `.docx` desde `~/pruebas-tareas/Downloads` a `~/pruebas-tareas/Documentos/PDF`. |
| `recoger-capturas` | Lleva capturas de pantalla del Escritorio a la carpeta Capturas. | Mover archivos `.png` cuyo nombre coincide con `^Captura de pantalla.*\.png$`, desde `~/pruebas-tareas/Desktop` a `~/pruebas-tareas/Capturas`. |
| `renombrar-fotos` | Cambia el nombre de fotos usando la fecha de modificación del archivo. | Renombrar archivos `.jpg`, `.jpeg`, `.png` y `.heic` de `~/pruebas-tareas/Fotos` con el formato `{fecha:%Y-%m-%d}_{n:03}{ext}`. |

La configuración también contiene una entrada llamada `Contar numero de letras`,
que aparece en la ayuda, pero todavía no implementa el recuento descrito: está
definida como una acción de tipo `mover`, con origen y destino `La actual`. No es
una acción funcional hasta que se complete su configuración y se implemente el
comportamiento esperado.

Las rutas de ejemplo usan `~/pruebas-tareas` para limitar las pruebas a una
carpeta separada de los archivos personales. Revisa las rutas de `acciones.json`
antes de ejecutar acciones sin `--simular`.

## Configurar acciones

Cada acción se define como un objeto dentro de la lista `acciones` del archivo
`acciones.json`. Debe incluir:

- `nombre`, `descripcion`, `tipo` y `origen`.
- `filtro`, con `extensiones` (lista de extensiones) o `patron` (expresión
  regular que se compara con el nombre del archivo).
- `destino` si `tipo` es `mover`.
- `plantilla` si `tipo` es `renombrar`.

Ejemplo de acción para mover PDF:

```json
{
  "nombre": "ordenar-pdf",
  "descripcion": "Mueve los PDF a una carpeta",
  "tipo": "mover",
  "origen": "~/Downloads",
  "filtro": {
    "extensiones": [".pdf"]
  },
  "destino": "~/Documents/PDF"
}
```

Las extensiones no distinguen entre mayúsculas y minúsculas. En una plantilla de
renombrado se pueden usar:

- `{fecha:FORMATO}`: fecha de modificación del archivo, con formato de Python
  `datetime`.
- `{n:FORMATO}`: número de secuencia de los archivos coincidentes.
- `{ext}`: extensión original del archivo.

Por ejemplo, `{fecha:%Y-%m-%d}_{n:03}{ext}` puede producir
`2026-10-31_001.jpg`.

## Límites actuales

- Los tipos de acción implementados son `mover` y `renombrar`.
- Los filtros se aplican a archivos de la carpeta de origen, no recorren
  subcarpetas.
- El programa no borra archivos. Al mover o renombrar, comprueba los destinos y
  aborta si ya existe un archivo con ese nombre.
- No están implementadas todavía las acciones con IA descritas en la
  especificación del proyecto.