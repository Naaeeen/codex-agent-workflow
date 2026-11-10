---
name: article-writing
description: "Draft or substantially revise articles, essays, tutorials, guides, and newsletter issues with clear structure, evidence, and an appropriate voice. Use for authored long-form content, not routine answers, code review explanations, or minor copy edits."
---

# Article Writing

Write long-form content that sounds like an actual person with a point of view, not an LLM smoothing itself into paste.

## When to Activate

- drafting blog posts, essays, launch posts, guides, tutorials, or newsletter issues
- turning notes, transcripts, or research into polished articles
- matching an existing founder, operator, or brand voice from examples
- tightening structure, pacing, and evidence in already-written long-form copy

## Core Rules

1. Lead with the concrete thing: artifact, example, output, anecdote, number, screenshot, or code.
2. Order context, examples and explanation for the reader; avoid one fixed opening formula.
3. Keep sentences tight unless the source voice is intentionally expansive.
4. Use proof instead of adjectives.
5. Never invent facts, credibility, or customer evidence.

## Voice Handling

If the user wants a specific voice, reuse the supplied examples, a confirmed voice profile, or style guidance already established by the active writing workflow. Use `brand-voice` when a new reusable profile is actually needed; do not require a second workflow or repeat completed analysis.

If no voice references are given, choose a clear tone appropriate to the audience and purpose, and preserve explicit user style preferences.

## Common formulaic symptoms

Use these as prompts to inspect meaning, not a detector or automatic replacement
list. Preserve quoted text, necessary technical language and the user's explicit
wording. Rewrite when the phrase delays the point, inflates it or adds no content:
- "In today's rapidly evolving landscape"
- "game-changer", "cutting-edge", "revolutionary"
- "here's why this matters" as a standalone bridge
- fake vulnerability arcs
- a closing question added only to juice engagement
- biography padding that does not move the argument
- generic AI throat-clearing that delays the point

## Writing Process

1. Infer the audience and purpose from the request and available context; ask only when a missing detail materially changes the draft.
2. Build a hard outline with one job per section.
3. Start sections with proof, artifact, conflict, or example.
4. Expand only where the next sentence earns space.
5. Cut anything that sounds templated, overexplained, or self-congratulatory.

## Structure Guidance

### Technical Guides

- open with what the reader gets
- use code, commands, screenshots, or concrete output in major sections
- end with actionable takeaways, not a soft recap

### Essays / Opinion

- start with tension, contradiction, or a specific observation
- keep one argument thread per section
- make opinions answer to evidence

### Newsletters

- keep the first screen doing real work
- do not front-load diary filler
- use section labels only when they improve scanability

## Quality Gate

Before delivering:
- factual claims are backed by supplied evidence or verified primary sources; clearly label uncertainty and opinion
- generic AI transitions are gone
- the voice matches the supplied examples or the agreed `VOICE PROFILE`
- every section adds something new
- formatting matches the intended medium

For a substantive revision, check the claim, supporting evidence, reasoning link
and scope before polishing sentences. Keep the original facts, numbers, attribution
and level of certainty. Read [meaning-first editing](references/meaning-first.md)
when generic prose or defensive hedging is the actual problem.
