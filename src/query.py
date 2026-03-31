"""Query processing for HR Helpdesk RAG."""

import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from .config import (
    CHROMA_PATH,
    TOP_K,
    RETRIEVAL_K,
    LLM_MODEL,
    LLM_TEMPERATURE,
    get_embedding_model,
    get_system_prompt,
)


def load_environment() -> None:
    """Load environment variables."""
    project_env = Path(__file__).resolve().parent.parent / ".env"
    if project_env.exists():
        load_dotenv(project_env)


def dedupe_docs(docs, max_docs: int = TOP_K):
    """Remove duplicate documents."""
    seen = set()
    unique = []
    
    for doc in docs:
        content = " ".join(doc.page_content.split())
        if not content:
            continue
        key = content.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(doc)
        if len(unique) >= max_docs:
            break
    
    return unique


def extract_sources(docs) -> list[dict]:
    """Extract unique sources from documents."""
    sources = []
    seen = set()
    
    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        source_name = str(metadata.get("source", "unknown"))
        if source_name in seen:
            continue
        seen.add(source_name)
        sources.append({"source": source_name})
    
    return sources


def is_small_talk(text: str) -> bool:
    """Return True for greetings and brief conversational messages."""
    normalized = re.sub(r"[^a-zA-Z\s]", "", text).strip().lower()
    if not normalized:
        return False

    small_talk_phrases = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "thanks",
        "thank you",
    }
    return normalized in small_talk_phrases


def query_rag(query: str, persist_directory: Optional[str] = None) -> dict:
    """Process a query using RAG."""
    load_environment()

    if is_small_talk(query):
        return {
            "answer": (
                "Hi! I can help with HR policy questions like leave, attendance, "
                "benefits, workplace conduct, and other company policy topics. "
                "Please ask your question, and I will answer from the available HR documents."
            ),
            "sources": [],
        }
    
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("Missing GROQ_API_KEY")
    
    if persist_directory is None:
        persist_directory = os.getenv("PERSIST_DIRECTORY", CHROMA_PATH)
    
    embedding_model = get_embedding_model()
    
    db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_model,
    )
    
    retriever = db.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    retrieved_docs = retriever.invoke(query)
    relevant_docs = dedupe_docs(retrieved_docs, max_docs=TOP_K)
    sources = extract_sources(relevant_docs)
    
    if not relevant_docs:
        return {"answer": "I don't have enough information from the documents.", "sources": []}
    
    combined_input = f"""
Based on the following HR documents, answer the question.

Question:
{query}

Documents:
{chr(10).join([f"- {doc.page_content}" for doc in relevant_docs])}

Provide a clear HR policy answer using only the provided documents.
If the information is not available, say:
"I don't have enough information from the documents."
"""
    
    model = ChatGroq(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=groq_key,
    )
    
    messages = [
        SystemMessage(content=get_system_prompt()),
        HumanMessage(content=combined_input),
    ]
    
    result = model.invoke(messages)
    
    return {"answer": result.content.strip(), "sources": sources}


if __name__ == "__main__":
    load_environment()
    result = query_rag("What is the company policy on discrimination?")
    print(result["answer"])
