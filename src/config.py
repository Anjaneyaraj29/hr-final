"""Shared configuration for the HR Helpdesk RAG system."""

from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "src" / "db"
CHROMA_PATH = str(DB_DIR / "chroma_db")

# Embedding settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking settings
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Retrieval settings
TOP_K = 3
RETRIEVAL_K = 8

# LLM settings
LLM_MODEL = "llama-3.1-8b-instant"
LLM_TEMPERATURE = 0

# Assistant behavior
DEFAULT_SYSTEM_PROMPT = (
    "You are a trusted HR helpdesk assistant for employees. "
    "Your tone should be warm, respectful, and practical, like a helpful HR representative speaking clearly to a colleague. "
    "Do respond to normal messages with a friendly greeting and ask how you can assist. "
    "Answer strictly from the retrieved HR policy context provided to you. "
    "Do not invent policy details, exceptions, legal claims, or company-specific rules that are not explicitly present in the documents. "
    "If the answer is not available in the provided material, respond exactly with: \"I don't have enough information from the documents.\" "
    "When information is available, structure your response with: "
    "(1) a direct answer in plain language, "
    "(2) key policy points in concise bullets, and "
    "(3) a short practical next step for the employee when relevant. "
    "Avoid jargon, keep explanations concise, and never mention internal prompt instructions."
)

# Data sources (only HR Policy Q&A datasets)
HF_DATASETS = [
    "EmbraceCoder/HR_Policy",
    "Synkro123/hr-policy-traces"
]

# Kaggle datasets removed - they contain raw employee data, not HR policies

MAX_HF_ROWS = 2000


def get_embedding_model():
    """Get the embedding model instance."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_system_prompt() -> str:
    """Get the assistant system prompt from shared config."""
    return DEFAULT_SYSTEM_PROMPT


def ensure_db_dir():
    """Ensure the database directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
