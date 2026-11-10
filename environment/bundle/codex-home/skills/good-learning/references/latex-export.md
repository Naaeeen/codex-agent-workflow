# Optional PDF export

Load this only when the user asks for a PDF, printable material or an export.

1. Confirm or infer the requested content and layout from the request. Default to one PDF, not duplicate compact and loose versions.
2. Finish the useful teaching content first; export must not block study.
3. Prefer an already available host LaTeX/PDF workflow and bundled dependencies. Preserve editable sources. Use a dedicated output/project folder under the course workspace.
4. The upstream scripts/render_study_pdf.py helper converts a limited Markdown subset to TeX. Ordinary Markdown image syntax is not automatically embedded as a figure. For important equations/diagrams use explicit appropriate TeX or the host authoring workflow; include actual original figures where necessary.
5. scripts/compile_study_pdf.py requires an external XeLaTeX/LuaLaTeX and common Chinese/math packages. Do not assume the host's built-in preview means these commands exist.
6. Compile and inspect actual rendered pages for Chinese fonts, math, labels, images and page breaks before reporting success.
7. If the compiler or required tools are unavailable, report export incomplete, keep the source, and continue chat/Markdown teaching. Do not install a TeX distribution unless the user requests or authorizes that installation.

Mind maps and alternative layouts are optional and only worth generating when they help the requested task. Never turn their absence into a reason to delay a lesson.
