# Changelog

Los cambios que notará quien USA la herramienta.
Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) · Versiones: [SemVer](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-19

### Añadido
- Instalación con una sola orden: `uv tool install git+https://github.com/JosepVidal1/cli-tareas@v1.0.0`.
- Órdenes `tareas version`, `listar`, `acciones`, `validar` y `ejecutar`.
- 5 acciones de sistema definidas en `acciones.json` para mover y renombrar archivos.
- Una acción encadenada (`secuencia`) que ejecuta varias acciones con una sola orden.
- 2 acciones con IA: resumir PDFs y proponer un nombre según el contenido del archivo.
- `--simular` para ver qué haría una acción sin tocar ningún archivo.
- `.env.example` con las variables que necesita la IA (sin claves reales).

### Cambiado
- Los errores de configuración y las acciones que no existen muestran un mensaje claro,
  sin trazas de Python, y salen con un código distinto de 0.

### Eliminado
- La acción de prueba «Contar numero de letras», porque no hacía lo que decía.