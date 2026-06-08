Put your past project documents here for RAG retrieval.

Supported file types:
- .txt
- .md
- .json
- .docx
- .pdf

Tips:
- Add one project per file when possible.
- Include problem, solution approach, stack, timeline, outcomes.
- Use clear headings so retrieval gets better matches.

After adding/updating files, restart `web_app.py` or call:
POST /api/kb/reindex

Note for PDF:
- PDF parsing uses `pypdf`. If not installed, PDF files are skipped.
- Install with: `pip install pypdf`

Vector RAG:
- Embeddings: `fastembed` text embeddings
- Vector DB: local Qdrant at `qdrant_data/`
- Collection name: `proposal_kb`
