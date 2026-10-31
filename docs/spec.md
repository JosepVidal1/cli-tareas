# Spec · tareas

- Para quién es: para mí, estudiante de DAM con un Mac, y para cualquiera que tenga el ordenador desordenado.
- Qué problema resuelve: ordenar, renombrar y entender archivos que se acumulan cada día, sin hacerlo a mano.
- Órdenes: tareas --help, version, listar, acciones, validar y ejecutar.
- Acciones de sistema:
  1. ordenar-descargas (mover): PDF y documentos (.pdf, .docx) de ~/Downloads a ~/Documents/PDF.
  2. recoger-capturas (mover): capturas del Escritorio ("Captura de pantalla…") a ~/Pictures/Capturas.
  3. renombrar-fotos (renombrar): IMG_4821.jpg → 2026-10-31_001.jpg (.jpg, .jpeg, .png, .heic).
  4. ordenar-imagenes (mover): imágenes de ~/Downloads a ~/Pictures/Descargadas.
  5. ordenar-instaladores (mover): .dmg y .pkg de ~/Downloads a ~/Downloads/Instaladores.
- Acción encadenada: limpieza-semanal ejecuta 1, 2, 4 y 5 con una sola orden.
- Acciones con IA (semana 3): resumir-pdf (resumen en Markdown de unos apuntes) y renombrar-por-contenido (propone un nombre leyendo el documento, siempre con --simular).
- Sin red: si no hay internet o falta la clave, las acciones con IA lo explican en una línea y el resto sigue funcionando.
- Seguridad: primero --simular; confirmación antes de sobrescribir; la clave de la IA solo en .env, que nunca se sube.
- Dónde pruebo: solo en ~/pruebas-tareas, nunca en mis archivos reales.
- Qué NO hará: no borra archivos, no sobrescribe sin preguntar y no sube mis archivos a internet (salvo el texto que envíe a la IA cuando yo lo pida).
- Sistemas: macOS (mi equipo), Linux (aula) y Windows.
