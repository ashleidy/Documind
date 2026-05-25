# config.py
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY         = os.environ.get('SECRET_KEY', 'documind-2024')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    CHROMA_PATH   = os.path.join(BASE_DIR, 'data', 'chroma_db')

    EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

    # Ollama local (fallback)
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    LLM_MODEL       = os.environ.get('LLM_MODEL', 'phi3')

    # Groq API gratuita 
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    USE_GROQ     = os.environ.get('USE_GROQ', 'false').lower() == 'true'
    GROQ_MODEL   = 'llama-3.1-8b-instant'  # el más rápido de Groq

    # RAG
    TOP_K_RESULTS = 3
    CHUNK_SIZE    = 600
    CHUNK_OVERLAP = 100