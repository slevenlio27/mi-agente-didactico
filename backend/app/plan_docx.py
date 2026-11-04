"""Exporta una planificación generada por la IA a un documento Word editable (.docx).

La IA escribe en texto plano (títulos en MAYÚSCULAS, listas con guiones). Aquí esa
estructura se convierte en estilos reales de Word —títulos, listas, negritas—, para que
el docente pueda editar, cambiar estilos o generar un índice como en cualquier documento.
"""

import datetime
import io
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

VERDE, TINTA, GRIS = RGBColor(0x1F, 0x8A, 0x73), RGBColor(0x16, 0x30, 0x2B), RGBColor(0x5A, 0x6B, 0x66)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

_BULLET = re.compile(r"^(\s*)[-•*–]\s+(.*)$")
_NUMBER = re.compile(r"^\s*(\d{1,2})[.)]\s+(.*)$")
_LABEL = re.compile(r"^([^:]{2,40}):\s+(.+)$")   # «Objetivo: …» → «Objetivo:» en negrita


def _limpia(texto: str) -> str:
    """Quita marcas de Markdown que la IA pudiera incluir pese a las instrucciones."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", texto)
    texto = texto.replace("`", "")
    return re.sub(r"^#{1,6}\s*", "", texto).strip()


MENORES = {"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en", "a", "al", "con", "por", "para", "un", "una", "sin", "sobre"}


def _titulo_legible(texto: str) -> str:
    """«EL CICLO DE CARNOT» → «El Ciclo de Carnot»: conserva los nombres propios (Carnot, Kelvin…)."""
    palabras = texto.lower().split(" ")
    salida = []
    for i, p in enumerate(palabras):
        inicio = i == 0 or palabras[i - 1].endswith((":", "—", "-")) or palabras[i - 1] in ("—", "-")
        salida.append(p if (not inicio and p in MENORES) else p[:1].upper() + p[1:])
    return " ".join(salida)


def _es_titulo(linea: str) -> bool:
    letras = [c for c in linea if c.isalpha()]
    return len(letras) >= 4 and linea == linea.upper() and len(linea) <= 120


def _texto_con_etiqueta(parrafo, texto):
    m = _LABEL.match(texto)
    if m:
        parrafo.add_run(m.group(1) + ": ").bold = True
        parrafo.add_run(m.group(2))
    else:
        parrafo.add_run(texto)


def _numero_de_pagina(parrafo):
    """Campo PAGE de Word: el número se actualiza solo."""
    run = parrafo.add_run(); run.font.size = Pt(8.5); run.font.color.rgb = GRIS
    for tipo, texto in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = texto
        run._r.append(el)


def _fecha(d: datetime.date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def build_plan_docx(contenido: str, titulo_doc: str, subtitulo: str = "", datos: list | None = None) -> bytes:
    """contenido: texto de la IA. datos: filas (etiqueta, valor) para la tabla inicial."""
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)          # carta
    sec.left_margin = sec.right_margin = Cm(2.3)
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.2)

    base = doc.styles["Normal"]; base.font.name = "Calibri"; base.font.size = Pt(11)
    base.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    base.paragraph_format.space_after = Pt(4)
    for nombre, tam, color in (("Title", 22, TINTA), ("Heading 1", 15, VERDE), ("Heading 2", 12.5, TINTA)):
        st = doc.styles[nombre]; st.font.name = "Calibri"; st.font.size = Pt(tam); st.font.color.rgb = color; st.font.bold = True
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    doc.styles["Heading 1"].paragraph_format.space_before = Pt(14)
    doc.styles["Heading 2"].paragraph_format.space_before = Pt(10)

    # Encabezado y pie de página
    enc = sec.header.paragraphs[0]; enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = enc.add_run("Mi Agente Didáctico"); r.font.size = Pt(8.5); r.font.color.rgb = GRIS
    pie = sec.footer.paragraphs[0]; pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = pie.add_run("Generado con Mi Agente Didáctico · Revísalo y ajústalo antes de usarlo en clase · Página ")
    r.font.size = Pt(8.5); r.font.color.rgb = GRIS
    _numero_de_pagina(pie)

    doc.add_paragraph(titulo_doc, style="Title")
    if subtitulo:
        p = doc.add_paragraph(); r = p.add_run(subtitulo); r.font.size = Pt(13); r.font.color.rgb = GRIS

    if datos:
        doc.add_paragraph("Datos de la planificación", style="Heading 1")
        tabla = doc.add_table(rows=0, cols=2); tabla.style = "Table Grid"; tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        tabla.autofit = False
        for etiqueta, valor in datos:
            celdas = tabla.add_row().cells
            celdas[0].width, celdas[1].width = Cm(5.5), Cm(11.4)
            celdas[0].paragraphs[0].add_run(str(etiqueta)).bold = True
            celdas[1].paragraphs[0].add_run(str(valor))
            sombra = OxmlElement("w:shd"); sombra.set(qn("w:val"), "clear"); sombra.set(qn("w:fill"), "E6F2EF")
            celdas[0]._tc.get_or_add_tcPr().append(sombra)
        # Anchos fijos en la cuadrícula de la tabla (Word y LibreOffice los respetan así)
        for col, ancho in zip(tabla.columns, (Cm(5.5), Cm(11.4))):
            col.width = ancho

    # Contenido: títulos, listas y párrafos con estilos de Word
    lineas = [l.rstrip() for l in (contenido or "").splitlines()]
    utiles = [l for l in lineas if l.strip()]
    if utiles and utiles[-1].strip().startswith("¿") and utiles[-1].strip().endswith("?"):
        ultima = utiles[-1]          # la pregunta final es para el chat, no para el documento
        lineas = lineas[: len(lineas) - 1 - lineas[::-1].index(ultima)]
    primer_titulo = True
    for bruta in lineas:
        if not bruta.strip() or set(bruta.strip()) <= set("-=_*|"):
            continue
        es_markdown_titulo = bruta.lstrip().startswith("#")
        texto = _limpia(bruta)
        if not texto:
            continue
        mb, mn = _BULLET.match(bruta), _NUMBER.match(bruta)
        if mb and not es_markdown_titulo:
            nivel = 2 if len(mb.group(1).replace("\t", "    ")) >= 2 else 1
            _texto_con_etiqueta(doc.add_paragraph(style="List Bullet 2" if nivel == 2 else "List Bullet"), _limpia(mb.group(2)))
        elif mn and not _es_titulo(texto):
            _texto_con_etiqueta(doc.add_paragraph(style="List Number"), _limpia(mn.group(2)))
        elif es_markdown_titulo or _es_titulo(texto):
            texto = texto.rstrip(":")
            doc.add_paragraph(_titulo_legible(texto) if texto.isupper() else texto,
                              style="Heading 1" if primer_titulo or "SESIÓN" not in texto.upper() else "Heading 2")
            primer_titulo = False
        else:
            _texto_con_etiqueta(doc.add_paragraph(), texto)

    buf = io.BytesIO(); doc.save(buf)
    return buf.getvalue()


def fecha_hoy() -> str:
    return _fecha(datetime.date.today())
