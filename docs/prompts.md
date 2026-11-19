# Cómo he usado la IA en este proyecto

Lo apunto con sinceridad: el curso pide trabajar con OpenCode, pero no pude asistir a la
tutoría de arranque y no conseguí conectarlo a los modelos del centro a tiempo. He trabajado con:

- **Claude (chat)**: como profesor. Me explicó cada paso y me ayudó a revisar y corregir errores.
- **GitHub Copilot en VS Code**: escribió buena parte del código (CLI, motor, IA, pruebas y CI).

Yo decidí qué hacía la herramienta (spec, acciones.json y ADR), probé cada cambio y hice los commits.

## Lo que escribí yo, con guía
- `docs/spec.md`: para quién es, mis acciones y qué NO hará.
- `acciones.json`: las 3 acciones, campo a campo, a mano.
- `docs/adr/0001-configuracion-externa.md`: por qué las acciones van en un JSON.

## Órdenes clave a Copilot (resumen; no guardé el texto exacto)
1. Separar la CLI y el motor en módulos (cli.py, motor.py, acciones.py, configuracion.py, errores.py).
2. Añadir acciones encadenadas y acciones con IA detrás de un proveedor (proveedor_ia.py).
3. Añadir pruebas con pytest y GitHub Actions en Linux, Windows y macOS.

## Lo que la IA hizo mal y corregí
- **Una acción que no funcionaba**: el asistente de "añadir-accion" creó "Contar numero de letras",
  de tipo "mover" y con origen "La actual". La quité porque no hacía lo que decía.
- **Tracebacks**: con una acción inexistente o un JSON roto salía la traza de Python, porque se usaba
  `typer.Exit` fuera de Typer. Lo cambié por `sys.exit` y el código 3 para configuración inválida.
- **Ruta con dos puntos**: mi carpeta se llamaba "Curs 26:27" y `uv run` fallaba
  ("path segment contains separator ':'"). La renombré a "Curs 26-27" y reinstalé el comando.
- **Sangría**: al editar a mano metí un `IndentationError`; lo detecté porque `tareas` dejó de funcionar.

## Lo que aprendí
- Lo que dice la IA hay que probarlo: varias cosas "parecían bien" y no lo estaban.
- Probar siempre en `~/pruebas-tareas` y con `--simular` antes de tocar ficheros reales.