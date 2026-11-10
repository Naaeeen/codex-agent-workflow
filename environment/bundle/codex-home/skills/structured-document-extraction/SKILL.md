---
name: structured-document-extraction
description: Extract tables, headings and structured text from complex local PDF or DOCX files with installed Docling when ordinary extraction is insufficient.
---

# Structured document extraction

Use the existing PDF/Office skill first for ordinary reading or editing. This is
an additional extraction route for tables, layout or a demonstrated extraction
failure; it does not author Office documents.

Use the unified pinned launcher, which selects the validated local model path
and isolated cache and disables telemetry/implicit Hugging Face credentials:
{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1 docling

In installed 2.147.0, use the convert subcommand; inspect docling convert --help.
For text PDFs, select --no-ocr and a task-owned output directory.
The validated model artifacts live at
{{CODEX_HOME}}\tools\docling\models. Keep this path for qualified
local PDF conversion; invoking the bare CLI may use a different cache or fetch
new model files. Prefer the local pipeline and do not enable remote services
implicitly. OCR models are not part of the prequalified artifact set.

- Retain input identity/hash and page/section references.
- Compare extracted structure with the actual page or source; a successful exit
  is not proof of correct table cells, reading order or complete text.
- Use selected pages and disable OCR when a text layer already works. Download
  only the required official model artifacts and record versions/licenses.
- Keep outputs task-local and do not upload private documents as a fallback.
- If extraction fails, preserve the failure and use another available reader;
  do not invent a value or silently replace missing content with zero.

For text-PDF reading-order failures, the launcher also provides pdf-layout:

`agent-tool.ps1 pdf-layout INPUT.pdf --output-dir TASK_DIR --pages 1,2 --layout two-column`

Choose two-column only when the request, source or rendered page establishes
left-column-first prose; otherwise use auto. Exit 0 means accepted under the
limited geometry checks; exit 2 means review_required, not successful extraction.
Always preserve the per-page status/reasons from extraction.json with the text.
For an established page region, add --crop x0,top,x1,bottom (PDF points,
top-left origin). The recorded scope is that region, not the whole page.
Bounds are explicit and validated; clipped words still require review.
The original failure and six extra boundary regressions are retained. On seven
supported synthetic layouts the supplement preserves order, with three 4×3
tables unchanged. This does not establish accuracy on arbitrary real papers.
Ambiguous headings, borderless/column-local tables, rotation and missing text
must remain review candidates; use page rendering/crops or another reader.
OCR/scanned pages, equations and the user's real documents remain unqualified.

Official documentation: https://docling-project.github.io/docling/
