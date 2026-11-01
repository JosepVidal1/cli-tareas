# ADR 0001 · Las acciones van en un archivo de configuración (acciones.json)

- Fecha: 2026-11-01
- Estado: aceptada

## Contexto
Mi CLI `tareas` ordena y renombra archivos: descargas, capturas de pantalla y fotos.
Empiezo con 3 acciones, pero quiero llegar a 5 o más, y añadir 2 con IA más adelante.

## Decisión
Las acciones se describen en `acciones.json` (nombre, tipo, origen, filtro y destino o plantilla).
El código no sabe qué acciones existen: las lee del archivo y las ejecuta.

## Alternativa descartada
Escribir cada acción como una función de Python dentro del código.
La descarto porque cada acción nueva me obligaría a tocar el código y podría romper lo que ya funciona.

## Consecuencias
- Ventaja: añadir una acción es añadir un bloque al JSON, sin tocar el código.
- Ventaja: otra persona puede crear sus propias acciones sin saber Python.
- Ventaja: puedo cambiar las rutas (de ~/pruebas-tareas a mis carpetas reales) sin programar.
- Inconveniente: si el JSON está mal escrito, el programa no lo entiende.
  Solución: la orden `tareas validar` dirá qué campo falla y saldrá con el código 3.
- Inconveniente: solo funcionan los tipos que el motor conoce (mover, renombrar…).
  Un tipo nuevo sí necesita programarse.