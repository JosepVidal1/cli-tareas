# ADR 0002 · Toda la IA pasa por una sola clase (ProveedorIA)

- Fecha: 2026-11-19
- Estado: aceptada
- Autor: Josep Vidal Durà

## Contexto
Mis acciones `resumir-pdf` y `renombrar-por-contenido` necesitan un modelo de lenguaje:
una regla no sabe de qué trata un PDF, hay que leerlo.
Quiero poder cambiar de servidor (el del centro, OpenAI u otro compatible) sin tocar las acciones,
y que la clave nunca acabe en el repositorio.

## Decisión
Toda llamada a un modelo pasa por la clase `ProveedorIA` (`src/tareas/proveedor_ia.py`),
con un método `completar(instrucciones, contenido)` que recibe texto y devuelve texto.
La configuración se lee de variables de entorno, nunca del código:
- `TAREAS_AI_API_KEY`: la clave (en `.env`, que está en `.gitignore` desde el primer commit).
- `TAREAS_AI_BASE_URL`: el servidor. Al usar la API de OpenAI, sirve también el del centro.
- `TAREAS_AI_MODEL`: el modelo.
`.env.example` documenta estas variables sin ningún valor real.

## Alternativas descartadas
1. **Llamar al servidor directamente desde cada acción.** Más rápido de escribir, pero repetiría
   el código de conexión y de errores en cada acción, y cambiar de servidor obligaría a tocarlas todas.
2. **Escribir la clave en el código o en acciones.json.** Descartado: se subiría a GitHub
   y cualquiera podría usarla.

## Consecuencias
- Ventaja: cambiar de servidor o de modelo es cambiar una variable, sin programar.
- Ventaja: las acciones sin IA no dependen de la clase, así que siguen funcionando sin red ni clave.
- Ventaja: la clave solo vive en mi equipo (`.env` o variables de entorno).
- Inconveniente: cada respuesta del modelo puede variar; por eso uso `--simular` antes de cambiar ficheros.
- Mejora futura: convertir `ProveedorIA` en una clase abstracta con una subclase por servidor
  y un proveedor falso para probar la IA sin red ni gastar tokens.