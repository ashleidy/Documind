# app/core/embedder.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config import Config
import os
import shutil

# El modelo de embeddings se descarga la primera vez (~120MB)
# Las siguientes veces se carga desde caché local
_embeddings_instance = None

def get_embeddings():
    """
    Singleton del modelo de embeddings.
    Se carga una sola vez para no desperdiciar memoria.
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        print("Cargando modelo de embeddings por primera vez...")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=Config.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("Modelo de embeddings listo.")
    return _embeddings_instance


def build_vectorstore(full_text: str, doc_id: str) -> Chroma:
    """
    1. Divide el texto en fragmentos
    2. Convierte cada fragmento en un vector numérico
    3. Guarda todo en ChromaDB (base de datos local)
    """
    # Limpiar base de datos anterior si existe
    doc_path = os.path.join(Config.CHROMA_PATH, doc_id)
    if os.path.exists(doc_path):
        shutil.rmtree(doc_path)

    # Dividir el texto en fragmentos manejables
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", ", ", " "],
        length_function=len
    )

    chunks = splitter.create_documents(
        texts=[full_text],
        metadatas=[{"doc_id": doc_id}]
    )

    print(f"Documento dividido en {len(chunks)} fragmentos.")

    # Crear la base vectorial
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=doc_path,
        collection_name=doc_id
    )

    print(f"Base vectorial creada con {len(chunks)} vectores.")
    return vectorstore


def load_vectorstore(doc_id: str) -> Chroma | None:
    """Carga una base vectorial ya existente para un documento."""
    doc_path = os.path.join(Config.CHROMA_PATH, doc_id)
    if not os.path.exists(doc_path):
        return None
    return Chroma(
        persist_directory=doc_path,
        embedding_function=get_embeddings(),
        collection_name=doc_id
    )


def vectorstore_exists(doc_id: str) -> bool:
    """Verifica si ya se procesó este documento."""
    doc_path = os.path.join(Config.CHROMA_PATH, doc_id)
    return os.path.exists(doc_path)
