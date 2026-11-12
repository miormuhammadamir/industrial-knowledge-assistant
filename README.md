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
flask --app run.py create-admin
```
The one-time command prompts for the initial administrator username, display name, and password. Password input is hidden, and the command refuses to run once an administrator exists. Set `SECRET_KEY` in `.env` for a chosen secret; otherwise IKA creates and persists a random key in the ignored `data` directory. Change the initial admin password from **Account & Admin → My profile** after sign-in.
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
Browser -> Flask Blueprints -> SQLite metadata / upload storage / background index worker -> PyMuPDF -> page- and heading-aware token chunks -> Ollama embeddings -> persistent ChromaDB and SQLite FTS5. Chat -> Ollama embedding plus keyword retrieval -> reciprocal-rank fusion -> bounded prompt -> Ollama generation -> citation records -> SQLite conversation.

## API
- `GET /api/dashboard/stats` counts
- `GET /api/documents` list, `POST /api/documents` multipart field `file`
- `GET /api/documents/{id}`, `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/reindex`, `GET /api/indexing/jobs/{id}`
- `POST /api/chat` JSON `{"question":"...","conversation_id":null,"document_ids":null}`
- `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`
- `GET /api/models`, `GET /api/system/health`

## Limitations and security
This is a functional starter implementation, not full specification compliance. Chunk budgets use the `cl100k_base` tokenizer as a practical estimate; it is not the exact tokenizer for every Ollama embedding model. Citations are mapped to retrieved passages only when the model emits `[SOURCE N]`; this does not independently verify claim-level entailment. Hybrid scores and vector distances are ranking diagnostics, not confidence scores. The background worker uses an in-process daemon and has no transactional cross-store recovery. Deleting documents may leave historical citation references. The app includes local user accounts, roles, and session-bound CSRF checks, but lacks OCR, advanced rate limiting, streaming, robust job cancellation, and production hardening. Do not expose this app on a public network. LLM responses must never be used as authoritative safety instructions.

## RAG evaluation and retrieval

Retrieval merges Chroma semantic results and SQLite FTS5 keyword results using reciprocal-rank fusion, then sends up to three passages to Ollama. The API response includes `retrieval_diagnostics` (chunk ID, page, distance, hybrid score, retrieval method, and answer-key detection). Citation identity is checked; factual entailment is not. `tests/test_rag_evaluation.py` contains offline golden cases for page citations and unsupported questions. Run all offline checks with `python -m pytest -q`. Evaluate against approved real documents before relying on answers, and never use this system as an authority for safety-critical work.

After changing chunking, reindex existing PDFs so their stored vectors reflect the new chunk boundaries.
