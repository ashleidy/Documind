# app/routes.py
from flask import (
    Blueprint, render_template, request,
    jsonify, current_app, session
)
from werkzeug.utils import secure_filename
import os, hashlib, shutil

from app.core.extractor import (
    extract_text_from_pdf, build_full_text, get_document_stats
)
from app.core.embedder import (
    build_vectorstore, load_vectorstore, vectorstore_exists
)
from app.core.qa_engine import answer_question
from app.utils.queue    import enqueue, get_job_status

main          = Blueprint('main', __name__)
active_stores = {}


def allowed_file(filename: str) -> bool:
    return filename.lower().endswith('.pdf')


def get_doc_id(filepath: str) -> str:
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read(8192))
    return hasher.hexdigest()[:16]


def clear_doc_cache(doc_id: str):
    if doc_id in active_stores:
        del active_stores[doc_id]
    doc_path = os.path.join(current_app.config['CHROMA_PATH'], doc_id)
    if os.path.exists(doc_path):
        shutil.rmtree(doc_path, ignore_errors=True)
        print(f"🗑 Cache eliminado: {doc_id[:8]}")


# ── Página principal ──────────────────────────────────────────
@main.route('/')
def index():
    return render_template('index.html')


# ── Subir PDF ─────────────────────────────────────────────────
@main.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400

    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Solo se aceptan PDFs"}), 400

    try:
        # Limpiar doc anterior de esta sesión
        prev_doc_id = session.get('current_doc_id')
        if prev_doc_id:
            clear_doc_cache(prev_doc_id)

        filename = secure_filename(file.filename)
        filepath = os.path.join(
            current_app.config['UPLOAD_FOLDER'], filename
        )
        file.save(filepath)
        doc_id = get_doc_id(filepath)
        session['current_doc_id'] = doc_id

        # Si ya existe en cache reutilizar
        if vectorstore_exists(doc_id) and doc_id in active_stores:
            os.remove(filepath)
            return jsonify({
                "success":  True,
                "doc_id":   doc_id,
                "filename": filename,
                "cached":   True
            })

        # Procesar nuevo documento
        pages       = extract_text_from_pdf(filepath)
        full_text   = build_full_text(pages)
        stats       = get_document_stats(pages)
        vectorstore = build_vectorstore(full_text, doc_id)
        active_stores[doc_id] = vectorstore
        os.remove(filepath)

        return jsonify({
            "success":  True,
            "doc_id":   doc_id,
            "filename": filename,
            "cached":   False,
            "stats":    stats
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


# ── Encolar pregunta ──────────────────────────────────────────
@main.route('/api/ask', methods=['POST'])
def ask():
    data     = request.get_json()
    question = data.get('question', '').strip()
    doc_id   = data.get('doc_id', '').strip()

    if not question:
        return jsonify({"error": "La pregunta está vacía"}), 400
    if not doc_id:
        return jsonify({"error": "No hay documento cargado"}), 400

    vectorstore = active_stores.get(doc_id) or load_vectorstore(doc_id)
    if not vectorstore:
        return jsonify({"error": "Documento no encontrado. Súbelo de nuevo."}), 404

    active_stores[doc_id] = vectorstore

    job_id = enqueue(
        answer_question,
        question=question,
        vectorstore=vectorstore
    )
    return jsonify({"job_id": job_id, "status": "pending"})


# ── Consultar resultado ───────────────────────────────────────
@main.route('/api/result/<job_id>', methods=['GET'])
def get_result(job_id: str):
    return jsonify(get_job_status(job_id))


# ── Limpiar cache ─────────────────────────────────────────────
@main.route('/api/clear', methods=['POST'])
def clear_cache():
    doc_id = session.get('current_doc_id')
    if doc_id:
        clear_doc_cache(doc_id)
        session.pop('current_doc_id', None)
    return jsonify({"success": True})


# ── Health check ──────────────────────────────────────────────
@main.route('/api/health')
def health():
    return jsonify({"status": "ok", "model": "groq+phi3"})