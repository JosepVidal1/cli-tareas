import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from tareas.errores import IAUnavailableError


class ProveedorIA:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        modelo: str | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("TAREAS_AI_API_KEY", "")).strip()
        self.base_url = (
            base_url if base_url is not None else os.getenv("TAREAS_AI_BASE_URL", "https://api.openai.com/v1")
        ).strip().rstrip("/")
        self.modelo = (modelo if modelo is not None else os.getenv("TAREAS_AI_MODEL", "gpt-4o-mini")).strip()

    def disponible(self) -> None:
        if not self.api_key:
            raise IAUnavailableError(
                "IA no disponible: configura TAREAS_AI_API_KEY en .env; las demás acciones siguen disponibles."
            )
        url = urlparse(self.base_url)
        if url.scheme not in {"http", "https"} or not url.netloc or not self.modelo:
            raise IAUnavailableError(
                "IA no disponible: revisa TAREAS_AI_BASE_URL y TAREAS_AI_MODEL en .env."
            )

    def completar(self, instrucciones: str, contenido: str) -> str:
        self.disponible()
        solicitud = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(
                {
                    "model": self.modelo,
                    "messages": [
                        {"role": "system", "content": instrucciones},
                        {"role": "user", "content": contenido},
                    ],
                    "temperature": 0.2,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(solicitud, timeout=30) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
        except HTTPError as error:
            raise IAUnavailableError(
                f"IA no disponible: el proveedor respondió HTTP {error.code}; inténtalo más tarde."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAUnavailableError(
                "IA no disponible: no se pudo conectar con el proveedor; comprueba la red y la configuración."
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IAUnavailableError("IA no disponible: el proveedor devolvió una respuesta inválida.") from error

        try:
            texto = datos["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise IAUnavailableError("IA no disponible: la respuesta no contiene el texto esperado.") from error
        if not isinstance(texto, str) or not texto.strip():
            raise IAUnavailableError("IA no disponible: el proveedor devolvió una respuesta vacía.")
        return texto.strip()
