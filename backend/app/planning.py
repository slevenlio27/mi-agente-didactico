"""«Planificar con IA»: análisis de un archivo → formulario → plan de clase o secuencia didáctica.

1. Gemini analiza el archivo y devuelve JSON con un esquema fijo (salida estructurada).
2. El backend limpia y valida ese JSON: nunca se confía a ciegas en la respuesta de la IA.
3. El docente responde el formulario; sus respuestas se validan contra las preguntas guardadas.
4. Con el archivo, las respuestas y el perfil docente, la IA genera la planificación.
"""

TIPOS_DOC = {
    "programa": "Programa o sílabo", "rubrica": "Rúbrica", "lectura": "Lectura o material",
    "examen": "Examen o evaluación", "plan": "Plan de clase", "otro": "Documento",
}
TIPOS_CAMPO = ("texto", "numero", "opcion", "multiple")
SALIDAS = ["Plan de clase por sesión", "Secuencia didáctica de la unidad"]

# Esquema JSON que Gemini debe cumplir (generationConfig.responseJsonSchema)
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_documento": {"type": "string", "enum": list(TIPOS_DOC)},
        "titulo": {"type": "string", "description": "Título breve del documento o de la unidad"},
        "resumen": {"type": "string", "description": "Resumen en 2 a 4 oraciones"},
        "hallazgos": {
            "type": "array", "description": "Lo relevante para planificar: objetivos, unidades, contenidos, evaluación, fechas",
            "items": {"type": "object", "properties": {"etiqueta": {"type": "string"}, "detalle": {"type": "string"}},
                      "required": ["etiqueta", "detalle"]},
        },
        "faltantes": {"type": "array", "items": {"type": "string"},
                      "description": "Información que falta en el documento para planificar bien"},
        "preguntas": {
            "type": "array", "description": "De 3 a 6 preguntas para completar la planificación",
            "items": {
                "type": "object",
                "properties": {
                    "pregunta": {"type": "string"},
                    "tipo": {"type": "string", "enum": list(TIPOS_CAMPO)},
                    "opciones": {"type": "array", "items": {"type": "string"}},
                    "sugerencia": {"type": "string", "description": "Valor sugerido (del perfil docente o del documento), o vacío"},
                },
                "required": ["pregunta", "tipo"],
            },
        },
    },
    "required": ["tipo_documento", "titulo", "resumen", "hallazgos", "faltantes", "preguntas"],
}

ANALYSIS_PROMPT = (
    "Analiza el archivo adjunto «{nombre}» para ayudar al docente a planificar sus clases.\n"
    "1. Identifica qué tipo de documento es y resume su contenido.\n"
    "2. Extrae lo relevante para planificar (objetivos, unidades, contenidos, evaluación, fechas, competencias).\n"
    "3. Señala qué información falta en el documento para planificar bien.\n"
    "4. Formula de 3 a 6 preguntas concretas para el docente, con el tipo de campo más cómodo de responder "
    "(numero para cantidades, opcion o multiple cuando hay alternativas claras, texto solo si es necesario). "
    "Usa la información del perfil del docente para sugerir valores cuando corresponda. "
    "No preguntes qué tipo de planificación quiere: esa pregunta ya la hace la plataforma.\n"
    "Responde en español."
)


def _txt(v, n):
    return " ".join(str(v or "").split())[:n]


def sanitize_analysis(data) -> dict:
    """Normaliza el JSON de la IA: tipos válidos, longitudes acotadas y la pregunta fija de salida."""
    if not isinstance(data, dict):
        raise ValueError("La respuesta no es un objeto JSON")
    tipo = data.get("tipo_documento") if data.get("tipo_documento") in TIPOS_DOC else "otro"
    hallazgos = [{"etiqueta": _txt(h.get("etiqueta"), 60), "detalle": _txt(h.get("detalle"), 400)}
                 for h in (data.get("hallazgos") or []) if isinstance(h, dict) and h.get("detalle")][:8]
    faltantes = [_txt(f, 200) for f in (data.get("faltantes") or []) if isinstance(f, str) and f.strip()][:5]

    preguntas = [{  # siempre primero: qué quiere generar el docente
        "id": "salida", "pregunta": "¿Qué quieres que genere?", "tipo": "opcion",
        "opciones": SALIDAS, "sugerencia": SALIDAS[0], "requerida": True,
    }]
    for i, q in enumerate((data.get("preguntas") or [])[:6], start=1):
        if not isinstance(q, dict) or not _txt(q.get("pregunta"), 200):
            continue
        tipo_c = q.get("tipo") if q.get("tipo") in TIPOS_CAMPO else "texto"
        opciones = [_txt(o, 80) for o in (q.get("opciones") or []) if isinstance(o, str) and o.strip()][:8]
        if tipo_c in ("opcion", "multiple") and len(opciones) < 2:
            tipo_c, opciones = "texto", []          # sin alternativas reales, mejor un campo de texto
        if tipo_c not in ("opcion", "multiple"):
            opciones = []
        preguntas.append({"id": f"q{i}", "pregunta": _txt(q.get("pregunta"), 200), "tipo": tipo_c,
                          "opciones": opciones, "sugerencia": _txt(q.get("sugerencia"), 200), "requerida": False})
    return {"tipo_documento": tipo, "titulo": _txt(data.get("titulo"), 120), "resumen": _txt(data.get("resumen"), 900),
            "hallazgos": hallazgos, "faltantes": faltantes, "preguntas": preguntas}


def analysis_to_text(a: dict, nombre: str) -> str:
    """Versión en texto del análisis: se guarda como mensaje y la IA la ve en el historial."""
    lines = [f"Análisis de «{nombre}» ({TIPOS_DOC[a['tipo_documento']]}): {a['titulo']}".strip(), "", a["resumen"]]
    if a["hallazgos"]:
        lines += ["", "Lo que encontré:"] + [f"- {h['etiqueta']}: {h['detalle']}" for h in a["hallazgos"]]
    if a["faltantes"]:
        lines += ["", "Lo que falta para planificar:"] + [f"- {f}" for f in a["faltantes"]]
    lines += ["", "Completa el formulario para generar tu planificación."]
    return "\n".join(lines)


def validate_answers(preguntas: list, answers: dict) -> dict:
    """Valida las respuestas contra las preguntas guardadas; ignora claves desconocidas."""
    if not isinstance(answers, dict):
        raise ValueError("Formato de respuestas inválido.")
    out = {}
    for q in preguntas:
        v = answers.get(q["id"])
        if v in (None, "", []):
            if q.get("requerida"):
                raise ValueError(f"Responde: {q['pregunta']}")
            continue
        if q["tipo"] == "numero":
            try:
                n = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"«{q['pregunta']}» debe ser un número.")
            if not 0 <= n <= 1000:
                raise ValueError(f"«{q['pregunta']}» está fuera de rango.")
            out[q["id"]] = int(n) if n == int(n) else n
        elif q["tipo"] == "opcion":
            if v not in q["opciones"]:
                raise ValueError(f"Elige una opción válida en «{q['pregunta']}».")
            out[q["id"]] = v
        elif q["tipo"] == "multiple":
            if not isinstance(v, list) or not all(x in q["opciones"] for x in v):
                raise ValueError(f"Elige opciones válidas en «{q['pregunta']}».")
            out[q["id"]] = v
        else:
            out[q["id"]] = _txt(v, 500)
    return out


def answers_summary(preguntas: list, answers: dict) -> str:
    """Mensaje visible del docente con sus respuestas."""
    lines = ["Respuestas del formulario:"]
    for q in preguntas:
        if q["id"] in answers:
            v = answers[q["id"]]
            lines.append(f"- {q['pregunta']} {', '.join(v) if isinstance(v, list) else v}")
    return "\n".join(lines)


FORMATO = ("Escribe en texto plano, legible en un chat: títulos en MAYÚSCULAS, listas con guiones "
           "y sin tablas ni símbolos de Markdown (#, **, |).")
INSTRUCCIONES = {
    "Plan de clase por sesión": (
        "Genera un PLAN DE CLASE POR SESIÓN basado en el archivo analizado, las respuestas del formulario "
        "y el perfil del docente. Para cada sesión incluye: objetivo de aprendizaje; contenidos; actividades de "
        "inicio, desarrollo y cierre con su tiempo en minutos (que sumen la duración de la clase); recursos; "
        "y evaluación formativa. "),
    "Secuencia didáctica de la unidad": (
        "Genera una SECUENCIA DIDÁCTICA DE LA UNIDAD basada en el archivo analizado, las respuestas del "
        "formulario y el perfil del docente. Incluye: competencias u objetivos de la unidad; secuencia de "
        "sesiones con el propósito de cada una; actividades por fase (apertura, desarrollo, cierre); "
        "evaluación (formativa y sumativa) con criterios; y recursos. "),
}


def generation_instructions(answers: dict) -> str:
    salida = answers.get("salida", SALIDAS[0])
    return INSTRUCCIONES.get(salida, INSTRUCCIONES[SALIDAS[0]]) + FORMATO + \
        " Al final, ofrece al docente ajustar algo concreto (duración, actividades o evaluación)."
