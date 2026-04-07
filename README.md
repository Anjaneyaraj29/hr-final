# HR Helpdesk RAG System

A Retrieval-Augmented Generation (RAG) system for HR helpdesk Q&A, built with Python, FastAPI, and Streamlit.

## Features

- **RAG Pipeline**: Combines vector search with LLM generation for accurate HR answers
- **Data Sources**: Loads HR policies from local `.txt` documents
- **FastAPI Backend**: RESTful API for querying the knowledge base
- **Streamlit UI**: User-friendly chat interface for employees

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
EMPLOYEE_DB_PATH=src/db/employee_auth.db
EMPLOYEE_CREDENTIALS=employee:employee123
```

`EMPLOYEE_CREDENTIALS` is now only used for first-run seed users. Passwords are stored as bcrypt hashes in the SQLite employee auth DB.

### Employee Credentials (Secure)

Add or update employee login credentials using:

```bash
python manage_employees.py --employee-id e1001 --full-name "John Doe" --role Employee --password "Pass@123"
```

If `--password` is omitted, the script prompts for it securely.

Then employees can log in using:
- Employee ID: `e1001`
- Password: `Pass@123`

On first app run, one default seeded employee is created from `EMPLOYEE_CREDENTIALS` if the auth database is empty.

### 3. Build Vector Store (One-time)

Place all HR policy `.txt` files in `data/documents/`, then run:

```bash
python main.py
```

This reads all `.txt` files from `data/documents/` and creates the vector index.

### 4. Start the API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at: http://localhost:8000/docs

### 5. Start the UI

```bash
streamlit run UI/chat.py
```

## Docker Setup

### Prerequisites

- Docker Desktop installed and running

### 1. Build and Start API + UI

```bash
docker compose up --build
```

Services:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501

### 2. One-time Data Ingestion (if vector DB is empty)

```bash
docker compose --profile setup run --rm ingest
```

### 3. Stop Containers

```bash
docker compose down
```

### 4. Persistent Data

The compose setup mounts `src/db` into containers, so these files persist on your machine:
- `src/db/chroma_db` (vector store)
- `src/db/employee_auth.db` (employee login DB)

## Project Structure

```
hr-final/
├── main.py              # Entry point
├── src/                 # Core RAG logic
│   ├── config.py       # Shared configuration
│   ├── ingest.py       # Data loading & indexing
│   └── query.py        # RAG query processing
├── api/                 # FastAPI server
│   └── main.py         # REST API endpoints
├── ui/                  # Streamlit UI
│   └── chat.py         # Chat interface
└── .env                # Environment variables
```

## API Usage

### Query Endpoint

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the leave policy?"}'
```

Response:
```json
{
  "query": "What is the leave policy?",
  "answer": "Based on the provided HR documents...",
      "sources": [{"source": "leave.txt"}]
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Architecture

```
User Input → API /ask → Query Engine → ChromaDB (vector search)
                                         ↓
                                   Retrieved Docs
                                         ↓
                                   Groq LLM (llama-3.1-8b-instant)
                                         ↓
                                   Generated Answer
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| LLM | Groq (llama-3.1-8b-instant) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Vector DB | ChromaDB |
| API | FastAPI |
| UI | Streamlit |
| Data | Local `.txt` files in `data/documents/` |

## Configuration

Settings are centralized in `src/config.py`:

```python
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 3              # Documents returned
RETRIEVAL_K = 8        # Documents retrieved before dedup
LLM_MODEL = "llama-3.1-8b-instant"
```

## License

MIT
