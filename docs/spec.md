# Especificación · tareas

- Para quién es: para un estudiante de DAM y cualquiera que quiera automatizar la organización de archivos.
- Problema: ordenar, renombrar y comprender documentos repetitivos sin modificar manualmente cada archivo.
- Órdenes: `version`, `listar`, `acciones`, `validar` y `ejecutar`; `--config` permite elegir otro JSON.
- Configuración: `acciones.json` define acciones `mover`, `renombrar`, `secuencia` y acciones de IA para PDFs.
- Acciones propias: ordenar descargas, recoger capturas, renombrar fotos, ordenar imágenes e instaladores; `limpieza-semanal` las combina.
- IA: `resumir-pdf` genera Markdown; `renombrar-por-contenido` propone nombres sin cambiar archivos.
- Seguridad: probar con `--simular`; no borrar ni sobrescribir; pedir confirmación antes de enviar texto a IA.
- Modo sin red: las funciones sin IA continúan disponibles; la orden IA informa si falta clave o conexión.
- Secretos: variables de IA en `.env`, ignorado por Git; `.env.example` no contiene claves reales.
- Pruebas: pytest usa carpetas temporales y no llama servicios de red ni modifica archivos personales.
- Sistemas: Linux, Windows y macOS; rutas gestionadas con `pathlib`, UTF-8 explícito y CI multiplataforma.
