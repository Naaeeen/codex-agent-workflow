---
name: exa-search
description: Use an available Exa integration for web, code, or company research when the user asks for Exa or the task calls for its specific capabilities. General research can use other available search tools.
---

# Exa Search

Neural search for web content, code, companies, and people via the Exa MCP server.

## When to Activate

- The user requests Exa, or its specific search capability fits a concrete research need.
- The Exa integration is available and its current tool schema has been checked.
- Ordinary search, documentation lookup, or a general research request alone does not require Exa. Use an already available suitable tool.

## MCP Requirement

First discover the tools actually available in this Codex session. Use Exa only
when its integration is present and appropriate; the tasks listed above do not
require installing it. If it is unavailable, use the current search/browser tools
for ordinary research and disclose the substitution when Exa was requested.

Do not edit Claude configuration from Codex, install an unverified npm server, or
enable a disabled integration merely because this skill was loaded. A requested
setup should use the current provider documentation and the host's supported MCP
configuration. Keep credentials in the supported secret store/environment and
never paste or print values. Existing scoped authorization still applies.

The tool names and parameters below are illustrative: use the installed tool's
schema, which can differ by server version. Cite primary sources for technical
claims. A hosted deep-research job is a separate external action: run it only when
authorized for the provider and any cost; ordinary research can continue locally.

## Core Tools

### web_search_exa
General web search for current information, news, or facts.

```
web_search_exa(query: "latest AI developments 2026", numResults: 5)
```

**Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | required | Search query |
| `numResults` | number | 8 | Number of results |

### web_search_advanced_exa
Filtered search with domain and date constraints.

```
web_search_advanced_exa(
  query: "React Server Components best practices",
  numResults: 5,
  includeDomains: ["github.com", "react.dev"],
  startPublishedDate: "2025-01-01"
)
```

**Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | required | Search query |
| `numResults` | number | 8 | Number of results |
| `includeDomains` | string[] | none | Limit to specific domains |
| `excludeDomains` | string[] | none | Exclude specific domains |
| `startPublishedDate` | string | none | ISO date filter (start) |
| `endPublishedDate` | string | none | ISO date filter (end) |

### get_code_context_exa
Find code examples and documentation from GitHub, Stack Overflow, and docs sites.

```
get_code_context_exa(query: "Python asyncio patterns", tokensNum: 3000)
```

**Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | required | Code or API search query |
| `tokensNum` | number | 5000 | Content tokens (1000-50000) |

### company_research_exa
Research companies for business intelligence and news.

```
company_research_exa(companyName: "Anthropic", numResults: 5)
```

**Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `companyName` | string | required | Company name |
| `numResults` | number | 5 | Number of results |

### people_search_exa
Find professional profiles and bios.

```
people_search_exa(query: "AI safety researchers at Anthropic", numResults: 5)
```

### crawling_exa
Extract full page content from a URL.

```
crawling_exa(url: "https://example.com/article", tokensNum: 5000)
```

**Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `url` | string | required | URL to extract |
| `tokensNum` | number | 5000 | Content tokens |

### deep_researcher_start / deep_researcher_check
Start an AI research agent that runs asynchronously.

```
# Start research
deep_researcher_start(query: "comprehensive analysis of AI code editors in 2026")

# Check status (returns results when complete)
deep_researcher_check(researchId: "<id from start>")
```

## Usage Patterns

### Quick Lookup
```
web_search_exa(query: "Node.js 22 new features", numResults: 3)
```

### Code Research
```
get_code_context_exa(query: "Rust error handling patterns Result type", tokensNum: 3000)
```

### Company Due Diligence
```
company_research_exa(companyName: "Vercel", numResults: 5)
web_search_advanced_exa(query: "Vercel funding valuation 2026", numResults: 3)
```

### Technical Deep Dive
```
# Start async research
deep_researcher_start(query: "WebAssembly component model status and adoption")
# ... do other work ...
deep_researcher_check(researchId: "<id>")
```

## Tips

- Use `web_search_exa` for broad queries, `web_search_advanced_exa` for filtered results
- Lower `tokensNum` (1000-2000) for focused code snippets, higher (5000+) for comprehensive context
- Combine `company_research_exa` with `web_search_advanced_exa` for thorough company analysis
- Use `crawling_exa` to get full content from specific URLs found in search results
- `deep_researcher_start` is best for comprehensive topics that benefit from AI synthesis

## Related Skills

- `deep-research` — Research workflow using the tools available in the current session
- `market-research` — Business-oriented research with decision frameworks
