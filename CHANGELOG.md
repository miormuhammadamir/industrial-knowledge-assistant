# Changelog

## 1.1.0 — RAG reliability patch
- Fetch eight retrieval candidates and rank down answer-key sections using a documented heuristic.
- Validate generated source indices against actual retrieved passages.
- Suppress misleading citations on explicit insufficient-evidence answers.
- Include retrieval diagnostics in `/api/chat` responses.
- Add five mocked regression tests.

Limitations: citation validation checks identity, not factual entailment; keyword heuristics can misclassify sections. No live Ollama/ChromaDB integration test was performed in this packaging environment.
