# app/core/qa_engine.py

from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from config import Config

# ─────────────────────────────────────────────────────────────
# PROMPT OPTIMIZADO PARA RAG DOCUMENTAL
# ─────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """
Eres DocuMind, un asistente experto en análisis documental y sistemas RAG.

OBJETIVO:
Responder preguntas usando EXCLUSIVAMENTE la información presente en el CONTEXTO.

========================
REGLAS OBLIGATORIAS
========================

1. Idioma:
- Responde SIEMPRE en español.

2. Uso del contexto:
- Usa SOLO la información contenida en el CONTEXTO.
- NO uses conocimiento externo.
- NO inventes datos, fechas, cifras, nombres o conclusiones.

3. Precisión:
- Si la respuesta existe parcialmente, indica claramente
  qué información sí aparece y cuál no.
- Si el contexto no contiene suficiente información responde EXACTAMENTE:
  "No encontré esa información en el documento."

4. Trazabilidad:
- Siempre menciona de qué fragmento proviene la información.
- Usa referencias tipo:
  [Fragmento 1]
  [Fragmento 2]

5. Calidad de respuesta:
- Sé claro, técnico y preciso.
- Evita respuestas vagas.
- No repitas información innecesaria.
- Prioriza exactitud sobre creatividad.

6. Formato:
- Para respuestas normales usa párrafos claros.
- Para resúmenes usa listas numeradas.
- Para comparaciones usa tablas o listas estructuradas.

7. Restricciones:
- NO asumas relaciones no explícitas.
- NO completes información faltante.
- NO hagas inferencias especulativas.

8. Contradicciones:
- Si distintos fragmentos contienen información diferente,
  menciona ambas versiones y aclara que existe una inconsistencia.

========================
CONTEXTO
========================

{context}

========================
PREGUNTA
========================

{question}

========================
RESPUESTA
========================
"""

# ─────────────────────────────────────────────────────────────
# INSTANCIAS GLOBALES
# ─────────────────────────────────────────────────────────────

_groq_instance = None
_ollama_instance = None


# ─────────────────────────────────────────────────────────────
# GROQ MODEL
# ─────────────────────────────────────────────────────────────

def get_groq_llm():
    """
    LLM de Groq:
    rápido, preciso y eficiente para múltiples usuarios.
    """
    global _groq_instance

    if _groq_instance is None:
        from langchain_groq import ChatGroq

        _groq_instance = ChatGroq(
            api_key=Config.GROQ_API_KEY,
            model_name=Config.GROQ_MODEL,
            temperature=0,      # máxima precisión documental
            max_tokens=1200,
        )

        print(f"✓ Groq listo ({Config.GROQ_MODEL})")

    return _groq_instance


# ─────────────────────────────────────────────────────────────
# OLLAMA MODEL
# ─────────────────────────────────────────────────────────────

def get_ollama_llm():
    """
    Modelo local Phi3 usando Ollama.
    Se usa como fallback cuando Groq falla.
    """
    global _ollama_instance

    if _ollama_instance is None:
        from langchain_ollama import OllamaLLM

        _ollama_instance = OllamaLLM(
            model=Config.LLM_MODEL,
            base_url=Config.OLLAMA_BASE_URL,

            temperature=0,

            num_predict=700,
            num_ctx=4096,

            num_gpu=0,
            keep_alive="30m",

            repeat_penalty=1.1,
        )

        print("✓ Ollama/Phi3 listo")

    return _ollama_instance


# ─────────────────────────────────────────────────────────────
# SELECCIÓN AUTOMÁTICA DE MODELO
# ─────────────────────────────────────────────────────────────

def get_llm():
    """
    Selecciona automáticamente el mejor modelo disponible.
    """

    if Config.USE_GROQ and Config.GROQ_API_KEY:
        return get_groq_llm(), "groq"

    return get_ollama_llm(), "ollama"


# ─────────────────────────────────────────────────────────────
# RESET MODELOS
# ─────────────────────────────────────────────────────────────

def reset_llm():
    global _groq_instance, _ollama_instance

    _groq_instance = None
    _ollama_instance = None

    print("⚠ Modelos reseteados")


# ─────────────────────────────────────────────────────────────
# QA ENGINE PRINCIPAL
# ─────────────────────────────────────────────────────────────

def answer_question(question: str, vectorstore: Chroma) -> dict:
    """
    Pipeline RAG:

    1. Recupera fragmentos relevantes
    2. Construye contexto enriquecido
    3. Genera respuesta precisa
    """

    # ─────────────────────────────────────────
    # PASO 1: RETRIEVAL SEMÁNTICO (MMR)
    # ─────────────────────────────────────────

    try:
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": Config.TOP_K_RESULTS,
                "fetch_k": 20
            }
        )

        docs = retriever.invoke(question)

    except Exception as e:
        return {
            "answer": f"Error buscando en el documento: {str(e)}",
            "sources": [],
            "success": False,
            "model": "error"
        }

    # ─────────────────────────────────────────
    # VALIDAR RESULTADOS
    # ─────────────────────────────────────────

    if not docs:
        return {
            "answer": "No encontré información relevante en el documento.",
            "sources": [],
            "success": False,
            "model": "none"
        }

    # ─────────────────────────────────────────
    # PASO 2: CONSTRUIR CONTEXTO
    # ─────────────────────────────────────────

    context_parts = []
    sources = []

    for i, doc in enumerate(docs):

        fragment = doc.page_content.strip()

        metadata = doc.metadata or {}

        source = metadata.get("source", "Documento")
        page = metadata.get("page", "N/A")

        formatted_fragment = f"""
[Fragmento {i + 1}]
Fuente: {source}
Página: {page}

Contenido:
{fragment}
"""

        context_parts.append(formatted_fragment)

        sources.append({
            "fragment": i + 1,
            "source": source,
            "page": page,
            "text": fragment[:300] + ("..." if len(fragment) > 300 else "")
        })

    # contexto más amplio
    context = "\n\n".join(context_parts)[:6000]

    # ─────────────────────────────────────────
    # PASO 3: CREAR PROMPT
    # ─────────────────────────────────────────

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE
    )

    # ─────────────────────────────────────────
    # PASO 4: OBTENER MODELO
    # ─────────────────────────────────────────

    llm, model_used = get_llm()

    # ─────────────────────────────────────────
    # PASO 5: GENERAR RESPUESTA
    # ─────────────────────────────────────────

    try:
        chain = prompt | llm

        answer = chain.invoke({
            "context": context,
            "question": question
        })

        # Groq devuelve AIMessage
        if hasattr(answer, "content"):
            answer = answer.content

        answer = answer.strip()

        return {
            "answer": answer,
            "sources": sources,
            "success": True,
            "model": model_used
        }

    # ─────────────────────────────────────────
    # FALLBACK AUTOMÁTICO
    # ─────────────────────────────────────────

    except Exception as e:

        error_msg = str(e)

        print(f"✗ Error con {model_used}: {error_msg}")

        # ─────────────────────────────────────
        # FALLBACK A OLLAMA
        # ─────────────────────────────────────

        if model_used == "groq":

            print("→ Intentando fallback con Phi3 local...")

            try:
                ollama_llm = get_ollama_llm()

                chain = prompt | ollama_llm

                answer = chain.invoke({
                    "context": context,
                    "question": question
                })

                if hasattr(answer, "content"):
                    answer = answer.content

                return {
                    "answer": answer.strip(),
                    "sources": sources,
                    "success": True,
                    "model": "ollama_fallback"
                }

            except Exception as e2:

                print(f"✗ Error fallback: {str(e2)}")

                reset_llm()

                return {
                    "answer": "Error en ambos modelos. Intenta nuevamente.",
                    "sources": [],
                    "success": False,
                    "model": "error"
                }

        # ─────────────────────────────────────
        # ERROR GENERAL
        # ─────────────────────────────────────

        reset_llm()

        return {
            "answer": "El modelo tardó demasiado o ocurrió un error.",
            "sources": [],
            "success": False,
            "model": "error"
        }