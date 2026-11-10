# Qualified local text-PDF layout reader

Use the pinned entrypoint:

```powershell
& '{{CODEX_HOME}}\tools\agent-kit\agent-tool.ps1' pdf-layout INPUT.pdf --output-dir TASK_DIR --pages 1,2 --layout two-column
```

The launcher uses this directory's isolated venv/Scripts/python.exe. Dependencies
are pinned with hashes in requirements-lock.txt; wheel and license records remain
alongside runtime-manifest.json. This runtime needs no model or remote service.

Default layout is auto. Select two-column only when the request, source or a
rendered page establishes left-column-first prose. Exit 0 means accepted under
the limited geometric contract; exit 2 means review_required. Preserve status,
reasons and source/page identities from extraction.json with extraction.md.
Conservation is not proof of source text or semantic reading order.

For a visually established page region, add --crop x0,top,x1,bottom in PDF points
using the top-left origin. Bounds apply to all selected pages and are validated.
Crop is explicit; no image is silently ignored. Output scope is cropped_region,
not the whole page. It records original coordinates and word coverage for that
region. Crops cutting words or retaining unsupported images still require review.

Qualification:31 tests, seven supported synthetic layouts ordered correctly,
three full4x3 table grids preserved, and six additional boundary PDF regressions.
One real public MapReduce paper page region was visually selected and checked
for section order and653/653 word conservation. This is not a real-paper benchmark.
The full page retains image warnings; a wrong prose profile can misorder a
borderless table. Empty documents are rejected. Rotated/vertical text, scans/OCR,
equations, sparse or ambiguous layouts and table topology remain bounded.

Sources:
- https://github.com/jsvine/pdfplumber#extracting-text
- https://docling-project.github.io/docling/reference/pipeline_options/
- https://research.google.com/archive/mapreduce-osdi04.pdf

Detailed local qualification and fixtures are preserved in
<PROJECT_ROOT>\2026-11-05\z\work\final-round\pdf.
