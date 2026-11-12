# Changelog

## 1.2.0 — Retrieval and indexing improvements
- Add page- and heading-aware chunking under a configurable token budget estimate.
- Merge SQLite FTS5 keyword results with Chroma vector candidates using reciprocal-rank fusion.
- Preserve existing vectors until replacement chunks are written and validate embedding batch sizes.
- Expose source numbers and retrieval methods in chat diagnostics and improve indexing error reporting.
- Add offline golden RAG cases and hybrid retrieval, chunking, and secret-key regression tests.
- Generate and persist a random local Flask secret when no usable secret is configured.

## 1.1.0 — RAG reliability patch
- Fetch eight retrieval candidates and rank down answer-key sections using a documented heuristic.
- Validate generated source indices against actual retrieved passages.
- Suppress misleading citations on explicit insufficient-evidence answers.
- Include retrieval diagnostics in `/api/chat` responses.
- Add five mocked regression tests.

Limitations: citation validation checks identity, not factual entailment; keyword heuristics can misclassify sections. No live Ollama/ChromaDB integration test was performed in this packaging environment.
