"""
Lógica de conexión con los proveedores de IA (OpenAI/ChatGPT, Google Gemini y
Anthropic/Claude). Por defecto usa las API keys del servidor (variables de
entorno); si el docente configuró su propia clave en "Preferencias de IA",
esa se usa en su lugar para sus conversaciones — así el consumo se factura
a su propia cuenta, no a la del servidor.
"""

import base64
import re

import requests

from .config import settings

# Segunda barrera de validación (además del esquema Pydantic de entrada):
# el nombre de modelo se pega directo en la URL de la API de Gemini, así
# que aunque ya se validó al recibir la petición, lo volvemos a validar
# aquí mismo, justo antes de construir esa URL.
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


class AIProviderError(Exception):
    """Error controlado para mostrar un mensaje amigable al usuario."""


# Formato de cada mensaje: {"role": "user"|"assistant", "content": str,
#                            "files": [{"name", "mime", "data": bytes}]}  (files opcional)
TEXT_MIMES = ("text/plain", "text/markdown")
MAX_TEXT_CHARS = 200_000


def _file_as_text(f) -> str:
    body = f["data"].decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
    return f"[Contenido del archivo «{f['name']}»]\n{body}\n[Fin del archivo]"


def _text_only(messages, provider_name):
    """Para proveedores donde solo enviamos texto: los archivos de texto se
    incorporan al mensaje; PDF e imágenes no se pueden enviar."""
    out = []
    for m in messages:
        files = m.get("files") or []
        if any(f["mime"] not in TEXT_MIMES for f in files):
            raise AIProviderError(
                f"{provider_name} en esta app solo lee archivos de texto. "
                "Para analizar PDF o imágenes, usa una conversación con Gemini."
            )
        text = "\n\n".join([_file_as_text(f) for f in files] + [m["content"]])
        out.append({"role": m["role"], "content": text})
    return out


def call_openai(messages, model="gpt-4o-mini", api_key=None, system=None):
    key = api_key or settings.OPENAI_API_KEY
    if not key:
        raise AIProviderError(
            "No hay clave de OpenAI disponible. Configúrala en Preferencias de IA o pide "
            "al administrador que configure OPENAI_API_KEY en el servidor."
        )
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + _text_only(messages, "ChatGPT")},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise AIProviderError("OpenAI tardó demasiado en responder. Intenta de nuevo.")
    except requests.exceptions.HTTPError:
        if resp.status_code == 401:
            raise AIProviderError("La clave de OpenAI configurada no es válida.")
        raise AIProviderError(f"OpenAI devolvió un error ({resp.status_code}).")
    except requests.exceptions.RequestException as e:
        raise AIProviderError(f"Error al conectar con OpenAI: {e}")


def call_gemini(messages, model=None, api_key=None, system=None):
    model = model or settings.GEMINI_MODEL
    key = api_key or settings.GEMINI_API_KEY
    if not key:
        raise AIProviderError(
            "No hay clave de Gemini disponible. Configúrala en Preferencias de IA o pide "
            "al administrador que configure GEMINI_API_KEY en el servidor."
        )
    if not _MODEL_PATTERN.match(model):
        # Nunca se debería llegar hasta aquí si el esquema de entrada ya
        # validó el modelo, pero si algo lo llama sin pasar por ahí, no
        # dejamos que un valor arbitrario termine dentro de la URL.
        raise AIProviderError(f"Nombre de modelo de Gemini inválido: {model!r}")

    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        parts = []
        for f in m.get("files") or []:
            if f["mime"] in TEXT_MIMES:
                parts.append({"text": _file_as_text(f)})
            else:
                # PDF e imágenes: Gemini los lee directamente (inline, base64)
                parts.append({"inline_data": {"mime_type": f["mime"], "data": base64.b64encode(f["data"]).decode()}})
        parts.append({"text": m["content"]})
        if contents and contents[-1]["role"] == role:
            # Dos mensajes seguidos del mismo rol (p. ej. una pregunta anterior que quedó sin
            # respuesta porque falló): Gemini exige alternar docente/IA, así que se combinan.
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": role, "parts": parts})
    body = {"contents": contents}
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            # La clave va en un encabezado, no en la URL: las URL quedan en registros
            # de servidores y proxies, y aparecían en los mensajes de error.
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body,
            # Un PDF largo con un modelo que "razona" puede tardar bastante más de 30 s
            timeout=settings.GEMINI_TIMEOUT,
        )
        resp.raise_for_status()
        return _gemini_text(resp.json())
    except requests.exceptions.Timeout:
        raise AIProviderError(
            f"Gemini tardó más de {settings.GEMINI_TIMEOUT} segundos en responder. Con archivos muy "
            "largos, prueba con uno más corto o vuelve a intentarlo."
        )
    except requests.exceptions.HTTPError:
        info = _google_error(resp)
        if resp.status_code in (400, 401, 403):
            if _is_key_error(info):
                raise AIProviderError("La clave de Gemini configurada no es válida.")
            if info is None:
                raise AIProviderError(
                    "No se pudo conectar con Gemini: la red bloqueó la conexión con Google "
                    "(proxy o firewall). Pide que se permita generativelanguage.googleapis.com."
                )
            raise AIProviderError(f"Gemini rechazó la solicitud: {info[1]}")
        if resp.status_code == 429:
            raise AIProviderError(
                "Se alcanzó el límite de uso de la clave de Gemini. Espera un rato o revisa "
                "tu cuota en https://aistudio.google.com (el nivel gratuito tiene límites diarios)."
            )
        if resp.status_code in (500, 502, 503, 504):
            raise AIProviderError("Gemini está saturado o tiene un problema temporal. Intenta de nuevo en unos minutos.")
        detail = f": {info[1]}" if info and info[1] else "."
        raise AIProviderError(f"Gemini devolvió un error ({resp.status_code}){detail}")
    except requests.exceptions.RequestException as e:
        raise AIProviderError(f"Error al conectar con Gemini: {e}")


def call_anthropic(messages, model="claude-sonnet-4-6", api_key=None, system=None):
    key = api_key or settings.ANTHROPIC_API_KEY
    if not key:
        raise AIProviderError(
            "No hay clave de Claude disponible. Configúrala en Preferencias de IA o pide "
            "al administrador que configure ANTHROPIC_API_KEY en el servidor."
        )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={"model": model, "max_tokens": 1024, "messages": _text_only(messages, "Claude"), **({"system": system} if system else {})},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(block["text"] for block in data["content"] if block["type"] == "text")
    except requests.exceptions.Timeout:
        raise AIProviderError("Claude tardó demasiado en responder. Intenta de nuevo.")
    except requests.exceptions.HTTPError:
        if resp.status_code == 401:
            raise AIProviderError("La clave de Claude configurada no es válida.")
        raise AIProviderError(f"Claude devolvió un error ({resp.status_code}).")
    except requests.exceptions.RequestException as e:
        raise AIProviderError(f"Error al conectar con Claude: {e}")


def _google_error(resp):
    """Si la respuesta es un error con el formato de Google, devuelve (status, mensaje, motivos).
    Si no (por ejemplo, la página de un proxy o firewall), devuelve None."""
    try:
        err = resp.json().get("error")
    except (ValueError, AttributeError):
        return None
    if not isinstance(err, dict):
        return None
    reasons = [d.get("reason", "") for d in err.get("details", []) if isinstance(d, dict)]
    return err.get("status", ""), str(err.get("message", ""))[:300], reasons


def _is_key_error(info) -> bool:
    """True solo si Google dice que el problema es la CLAVE (inválida, vencida o sin
    permiso para esta API). Otros errores 400, como una petición mal formada, no lo son."""
    if info is None:
        return False
    status, message, reasons = info
    if any(r.startswith("API_KEY") or r in ("SERVICE_DISABLED", "CONSUMER_INVALID") for r in reasons):
        return True
    return status in ("UNAUTHENTICATED", "PERMISSION_DENIED") or "api key" in message.lower()


def _google_rejected_key(resp) -> bool:
    return _is_key_error(_google_error(resp))


_BLOCK_REASONS = {
    "SAFETY": "sus filtros de seguridad",
    "RECITATION": "que la respuesta reproducía demasiado texto protegido",
    "PROHIBITED_CONTENT": "su política de contenido",
    "BLOCKLIST": "su política de contenido",
}


def _gemini_text(data) -> str:
    """Extrae el texto de la respuesta. Los modelos que "razonan" pueden devolver varias
    partes (algunas son solo razonamiento interno, marcadas como "thought"); se unen las
    de texto visible. Si Google no devolvió respuesta, se explica por qué."""
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "")
        why = _BLOCK_REASONS.get(reason, "una restricción de Google")
        raise AIProviderError(f"Gemini no respondió a esta consulta por {why}. Prueba reformulándola.")
    cand = candidates[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if text.strip():
        return text
    finish = cand.get("finishReason", "")
    if finish in _BLOCK_REASONS:
        raise AIProviderError(f"Gemini no completó la respuesta por {_BLOCK_REASONS[finish]}. Prueba reformulando la consulta.")
    if finish == "MAX_TOKENS":
        raise AIProviderError("La respuesta de Gemini superó el largo máximo. Pide una respuesta más breve o por partes.")
    raise AIProviderError("Gemini devolvió una respuesta vacía. Vuelve a intentarlo.")


def validate_gemini_key(key: str):
    """Comprueba una clave con Google sin gastar cuota de generación.
    Devuelve True (válida), False (rechazada) o None (no se pudo comprobar)."""
    try:
        resp = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": key},
            params={"pageSize": 1},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None
    if resp.status_code == 200:
        return True
    if resp.status_code in (400, 401, 403) and _google_rejected_key(resp):
        return False
    return None  # no se pudo comprobar (red bloqueada, Google caído, etc.)


PROVIDERS = {
    "openai": call_openai,
    "gemini": call_gemini,
    "anthropic": call_anthropic,
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": settings.GEMINI_MODEL,
    "anthropic": "claude-sonnet-4-6",
}


def get_ai_response(provider: str, messages, model: str = None, api_key: str = None, system: str = None) -> str:
    if provider not in PROVIDERS:
        raise AIProviderError(f"Proveedor de IA desconocido: {provider}")
    fn = PROVIDERS[provider]
    return fn(messages, model or DEFAULT_MODELS[provider], api_key=api_key, system=system)
