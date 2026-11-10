---
name: brand-voice
description: "Create or update a reusable writing voice profile from representative source material when the user requests voice analysis, brand voice guidance, or consistency across multiple outputs. Reuse an existing confirmed profile; ordinary drafting and minor edits do not require a separate profiling workflow."
---

# Brand Voice

Build a durable voice profile from real source material, then use that profile everywhere instead of re-deriving style from scratch or defaulting to generic AI copy.

## When to Activate

- the user wants content or outreach in a specific voice
- the user wants a reusable profile spanning channels such as X, LinkedIn, email, or product updates
- adapting a known author's tone across channels
- the existing content lane needs a reusable style system instead of one-off mimicry

## Source Priority

Use the user-designated sources first, then representative material from the target channel and context. The following are possible sources, not a mandatory priority order:

1. recent original X posts and threads
2. articles, essays, memos, launch notes, or newsletters
3. real outbound emails or DMs that worked
4. product docs, changelogs, README framing, and site copy

Do not use generic platform exemplars as source material.

## Collection Workflow

1. Gather 5 to 20 representative samples when available.
2. Prefer recent material over old material unless the user says the older writing is more canonical.
3. Separate "public launch voice" from "private working voice" if the source set clearly splits.
4. Use supplied samples or a confirmed profile first. Retrieve additional original posts only if they are relevant and needed, using an available authorized read-only source; X access is not a prerequisite for drafting.
5. If site copy matters, inspect the actual subject's relevant pages. Include ECC material only when the requested voice or subject is Affaan/ECC.

## What to Extract

- rhythm and sentence length
- compression vs explanation
- capitalization norms
- parenthetical use
- question frequency and purpose
- how sharply claims are made
- how often numbers, mechanisms, or receipts show up
- how transitions work
- what the author never does

## Output Contract

Produce a reusable `VOICE PROFILE` block that downstream skills can consume directly. Use the schema in [references/voice-profile-schema.md](references/voice-profile-schema.md).

Keep the profile structured and short enough to reuse in session context. The point is not literary criticism. The point is operational reuse.

## Affaan / ECC Defaults

If the user wants Affaan / ECC voice and live sources are thin, start here unless newer source material overrides it:

- direct, compressed, concrete
- specifics, mechanisms, receipts, and numbers beat adjectives
- parentheticals are for qualification, narrowing, or over-clarification
- capitalization is conventional unless there is a real reason to break it
- questions are rare and should not be used as bait
- tone can be sharp, blunt, skeptical, or dry
- transitions should feel earned, not smoothed over

## Patterns to Evaluate

Avoid these when unsupported by the requested voice. Explicit style guidance and representative sources can justify them; do not turn ECC preferences into every author's rules:

- fake curiosity hooks
- "not X, just Y"
- "no fluff"
- forced lowercase
- LinkedIn thought-leader cadence
- bait questions
- "Excited to share"
- generic founder-journey filler
- corny parentheticals

## Persistence Rules

- Reuse the latest confirmed `VOICE PROFILE` across related tasks in the same session.
- If the user asks for a durable artifact, save it in the requested workspace location. Change personal memory only when the user explicitly asks for a memory update and the host supports it.
- Do not create repo-tracked files that store personal voice fingerprints unless the user explicitly asks for that.

## Downstream Use

Use this skill before or inside:

- `content-engine`
- `crosspost`
- `lead-intelligence`
- article or launch writing
- cold or warm outbound across X, LinkedIn, and email

Reuse a confirmed profile or an active writing workflow's style analysis. Do not impose another profiling pass or replace explicit user guidance; use this skill only when a reusable profile is needed.
