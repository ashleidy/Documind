# app/core/extractor.py
import fitz          # PyMuPDF
import os

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Lee el PDF página por página y devuelve una lista
    con el número de página y el texto de cada una.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"No se encontró el PDF: {pdf_path}")

    doc     = fitz.open(pdf_path)
    pages   = []

    for num in range(len(doc)):
        page = doc[num]
        text = page.get_text("text").strip()

        # Ignorar páginas vacías (imágenes sin OCR, páginas en blanco)
        if len(text) > 30:
            pages.append({
                "page":  num + 1,
                "text":  text,
                "chars": len(text)
            })

    doc.close()

    if not pages:
        raise ValueError(
            "No se pudo extraer texto del PDF. "
            "Puede ser un PDF escaneado (solo imágenes). "
            "Por ahora solo se soportan PDFs con texto."
        )

    return pages


def build_full_text(pages: list[dict]) -> str:
    """
    Une todas las páginas en un solo texto,
    marcando el número de página para que el modelo
    pueda citar de dónde viene cada parte.
    """
    parts = []
    for p in pages:
        parts.append(f"[PÁGINA {p['page']}]\n{p['text']}")
    return "\n\n".join(parts)


def get_document_stats(pages: list[dict]) -> dict:
    """Estadísticas básicas del documento."""
    total_chars = sum(p["chars"] for p in pages)
    return {
        "total_pages": len(pages),
        "total_chars": total_chars,
        "estimated_words": total_chars // 5,
        "pages_with_text": len(pages)
    }
