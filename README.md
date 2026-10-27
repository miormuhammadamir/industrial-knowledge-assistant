# Industrial Knowledge Assistant (IKA)

Local-first Flask / SQLite / ChromaDB / Ollama retrieval-augmented generation application. Intended for trusted single-user local operation only. **Not production-ready or suitable for public exposure.**

## Windows installation
1. Install Python 3.11 and Ollama separately.
2. In VS Code PowerShell, from the project folder:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```
3. In a terminal with Ollama running:
```powershell
ollama pull llama3.2:3b
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```
4. Start with `python run.py` and open http://127.0.0.1:5000.
5. Upload a text-based PDF and wait for indexing; then ask a question.
6. Test offline components with `python -m pytest -q`.

## Architecture
Browser -> Flask Blueprints -> SQLite metadata / upload storage / background index worker -> PyMuPDF -> word-based overlapping chunks -> Ollama embeddings -> persistent ChromaDB. Chat -> Ollama embedding -> Chroma search -> bounded prompt -> Ollama generation -> citation records -> SQLite conversation.

## API
- `GET /api/dashboard/stats` counts
- `GET /api/documents` list, `POST /api/documents` multipart field `file`
- `GET /api/documents/{id}`, `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/reindex`, `GET /api/indexing/jobs/{id}`
- `POST /api/chat` JSON `{"question":"...","conversation_id":null,"document_ids":null}`
- `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`
- `GET /api/models`, `GET /api/system/health`

## Limitations and security
This is a functional starter implementation, not full specification compliance. Chunking is **word-based**, not token-aware. Citations are mapped only when the model emits `[SOURCE N]`; no independent claim-level verification exists. Background worker uses an in-process daemon and has no transactional cross-store recovery. Deleting documents may leave historical citation references. No OCR, multi-user login, CSRF protection for publicly exposed instances, advanced rate limiting, streaming, or robust job cancellation. Do not expose this app on a public network. Some processing failures can leave partial vector writes; reindex to recover. LLM responses must never be used as authoritative safety instructions. Local Ollama and Chroma integration remain to be verified on your computer.
