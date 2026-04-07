"""Data ingestion and indexing for HR Helpdesk RAG."""

from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from .config import (
        CHROMA_PATH,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        DOCUMENTS_DIR,
        get_embedding_model,
        ensure_db_dir,
    )
except ImportError:
    from config import (
        CHROMA_PATH,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        DOCUMENTS_DIR,
        get_embedding_model,
        ensure_db_dir,
    )


def load_local_documents(documents_dir: str = DOCUMENTS_DIR) -> list[Document]:
    """Load all .txt files from a local directory."""
    print(f"Loading local documents from: {documents_dir}")
    
    doc_path = Path(documents_dir)
    if not doc_path.exists():
        print(f"WARNING: Documents directory not found: {documents_dir}")
        return []
    
    documents = []
    txt_files = sorted(doc_path.glob("**/*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in {documents_dir}")
        return []
    
    for txt_file in txt_files:
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            if content:
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": txt_file.name,
                            "path": str(txt_file.relative_to(doc_path)),
                        },
                    )
                )
        except Exception as e:
            print(f"Error reading {txt_file.name}: {e}")
    
    print(f"Loaded {len(documents)} documents from local files")
    return documents


def load_all_documents() -> list[Document]:
    """Load all HR documents from local .txt files."""
    print("Loading all HR documents...")
    
    documents = load_local_documents()
    
    print(f"Total documents loaded: {len(documents)}")
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """Split documents into chunks."""
    print("Splitting documents...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Total chunks created: {len(chunks)}")
    
    return chunks


def create_vector_store(chunks: list[Document], persist_directory: str = None) -> Chroma:
    """Create and persist the vector store."""
    if persist_directory is None:
        persist_directory = CHROMA_PATH
    
    if not chunks:
        raise ValueError("No chunks provided for indexing")
    
    print(f"Creating vector store at: {persist_directory}")
    ensure_db_dir()
    
    embedding_model = get_embedding_model()
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_directory
    )
    
    print("Vector store created successfully")
    return vectorstore


def ingest() -> None:
    """Main ingestion pipeline."""
    documents = load_all_documents()
    chunks = split_documents(documents)
    create_vector_store(chunks)
    print("Ingestion complete!")


if __name__ == "__main__":
    load_dotenv()
    ingest()
