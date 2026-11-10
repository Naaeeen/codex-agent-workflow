---
name: deep-research
description: Research a question in depth using available search and source-reading tools, then synthesize a cited report with source quality, uncertainty, and decision-relevant findings.
---

# Deep Research

Produce thorough, cited research reports from multiple sources using the search and reading tools available in the current session.

## When to Activate

- User asks to research any topic in depth
- Competitive analysis, technology evaluation, or market sizing
- Due diligence on companies, investors, or technologies
- Any question requiring synthesis from multiple sources
- User says "research", "deep dive", "investigate", or "what's the current state of"

## Tool Selection

Discover and use existing capabilities: native web search/open, relevant connected sources, or installed Firecrawl/Exa tools. These providers are alternatives, not prerequisites. Verify actual tool names and schemas before calling them; examples below illustrate query intent, not guaranteed current APIs.

Do not install an MCP server, change global configuration, buy a service, or upload private context solely to follow this skill. If a source cannot be read with available tools, identify the gap and continue with accessible primary evidence. Do not claim blocked sources were reviewed.

## Workflow

### Step 1: Understand the Goal

Infer the decision, scope, depth, and constraints from the request and available context. Ask only when missing information would materially change the research; continue independent work while waiting. When reasonable assumptions suffice, state them and proceed.

### Step 2: Plan the Research

Break the topic into a manageable set of independent research sub-questions, scaled to the decision. Example:
- Topic: "Impact of AI on healthcare"
  - What are the main AI applications in healthcare today?
  - What clinical outcomes have been measured?
  - What are the regulatory challenges?
  - What companies are leading this space?
  - What's the market size and growth trajectory?

### Step 3: Execute Multi-Source Search

For each sub-question, search using an available provider. Native web tools are sufficient; if installed, Firecrawl or Exa can provide useful search or extraction capabilities.

**With firecrawl:**
```
firecrawl_search(query: "<sub-question keywords>", limit: 8)
```

**With exa:**
```
web_search_exa(query: "<sub-question keywords>", numResults: 8)
web_search_advanced_exa(query: "<keywords>", numResults: 5, startPublishedDate: "<date-relevant-to-the-question>")
```

**Search strategy:**
- Vary keywords when results miss a relevant angle; do not repeat equivalent searches solely to meet a count.
- Use news-focused queries when event timing matters, and distinguish publication dates from event dates.
- Gather enough independent sources to resolve the material claims and contradictions; a source-count target is not a quality measure.
- Prefer primary documentation, original research, and firsthand evidence. For technical claims use official docs, source code, or original papers. Treat practitioner examples as context-dependent evidence, not universal instructions.

### Step 4: Deep-Read Key Sources

For the most promising URLs, fetch full content:

**With firecrawl:**
```
firecrawl_scrape(url: "<url>")
```

**With exa:**
```
crawling_exa(url: "<url>", tokensNum: 5000)
```

Read the relevant full sections of decisive sources, including limitations and version dates. Do not rely only on search snippets. If complete access is unavailable, distinguish excerpt-based findings from full-source review.

### Step 5: Synthesize and Write Report

Structure the report:

```markdown
# [Topic]: Research Report
*Generated: [date] | Sources: [N] | Confidence: [High/Medium/Low]*

## Executive Summary
[3-5 sentence overview of key findings]

## 1. [First Major Theme]
[Findings with inline citations]
- Key point ([Source Name](url))
- Supporting data ([Source Name](url))

## 2. [Second Major Theme]
...

## 3. [Third Major Theme]
...

## Key Takeaways
- [Actionable insight 1]
- [Actionable insight 2]
- [Actionable insight 3]

## Sources
1. [Title](url) — [one-line summary]
2. ...

## Methodology
Searched [N] queries across web and news. Analyzed [M] sources.
Sub-questions investigated: [list]
```

### Step 6: Deliver

- **Short topics**: Post the full report in chat
- **Long reports**: Post the executive summary + key takeaways, save full report to a file

## Parallel Research with Subagents

For broad topics, use available local collaboration/subagent tools for independent bounded questions when they improve speed or confidence. Use actual available roles, such as `docs_researcher` or a general agent; do not assume Claude's `Task` tool exists. If delegation is unavailable, use the same passes sequentially. Remote agent dispatch requires the user's explicit authorization.

```
Launch 3 research agents in parallel:
1. Agent 1: Research sub-questions 1-2
2. Agent 2: Research sub-questions 3-4
3. Agent 3: Research sub-question 5 + cross-cutting themes
```

Give each agent its question, constraints, raw sources if useful, expected evidence, and a completion condition. Keep research read-only. Each agent returns findings, source URLs, dates/versions, uncertainties, and conflicting evidence. The parent resolves disagreements and verifies claims used in the final report.

## Quality Rules

1. **Support material factual claims.** Cite sources next to the claims they support. Label your recommendations and reasoning as judgments rather than attributing them to a source.
2. **Cross-reference where it matters.** Seek independent corroboration for disputed or consequential claims. One authoritative API reference can establish documented behavior; several copied articles are not independent verification.
3. **Match recency to the question.** Verify current APIs and installed versions, and use primary historical sources for historical claims. Do not replace decisive evidence merely because it is older than 12 months.
4. **Acknowledge gaps.** If you couldn't find good info on a sub-question, say so.
5. **No hallucination.** If you don't know, say "insufficient data found."
6. **Separate fact from inference.** Label estimates, projections, and opinions clearly.

## Examples

```
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research the best strategies for bootstrapping a SaaS business"
"What's happening with the US housing market right now?"
"Investigate the competitive landscape for AI code editors"
```

For noisy saved HTML, the installed local Trafilatura route can extract a reading
candidate without uploading it. See [saved HTML extraction](references/local-html.md).
Keep the source and recheck important quotations/omissions against it.
