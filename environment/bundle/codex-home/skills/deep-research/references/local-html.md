# Saved HTML extraction

Prefer the connected/browser source when it already supplies readable evidence.
For authorized local saved HTML, the pinned `agent-tool.ps1 trafilatura` route
accepts raw HTML on stdin. Use `--fast --precision --no-comments --with-metadata --json`.
Read with an explicit UTF-8 encoding. Its -i option expects a URL list, not an HTML
file. The package does not support `python -m trafilatura` in this installation.

Retain the original HTML identity/hash, URL and retrieval date separately. Check
key text and metadata against the original. Empty output is an abstention, not
an empty original article. The tested default fallback admitted navigation-only
text; fast/precision avoided that fixture while retaining the article. This is
not a universal extraction-accuracy claim. JavaScript-rendered text may require
the existing browser tools. Do not start crawling or remote extraction implicitly.

Source: https://trafilatura.readthedocs.io/en/latest/usage-cli.html#process-files-locally
