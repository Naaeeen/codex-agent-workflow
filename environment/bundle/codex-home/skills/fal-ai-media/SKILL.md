---
name: fal-ai-media
description: Use fal.ai when the user requests or selects that provider for image, video, or audio generation. Check live models, schema, upload scope and cost before an authorized job; ordinary image requests can use native image generation.
---

# Use fal.ai for a Selected Media Task

Use the provider the user chose. A general request for an image, thumbnail, narration or video does not by itself select fal.ai. Prefer the host's available native media tools when they satisfy an ordinary request. Never silently switch providers or set up another service because a sample names it.

## Resolve the actual capability

1. Discover the available fal.ai tools or the project's existing client. Verify the installed interface and current official documentation. If unavailable, explain that limitation and use an appropriate available alternative only within the user's requested scope.
2. Match supported models to output type, editing/reference needs, quality, latency and the authorized budget. Keep a user-selected model when supported; if unavailable, explain before choosing an alternative. Example names or an upstream release date are not a current ranking.
3. Read the selected model's actual input/output schema: aspect ratio, duration, resolution, seed support, reference-media format and async behavior vary. Do not copy one model's fields into another.

## Execute and verify

- Before an upload or paid generation, establish the selected provider, exact input scope and expected cost under current task authorization. Existing scoped authorization counts; do not print credentials or ask for keys in chat.
- Use supported local/environment secret handling. Setup is a separate concrete task, not an implicit permission to modify global MCP configuration.
- Submit only the authorized input. Track the returned job ID through the provider's actual status/result interface; queued or running is not complete. Respect rate limits and use bounded retries for transient errors. Check job status before resubmitting a timeout that might have already created a paid job.
- Inspect the result and error fields before declaring success: a completed queue request can still contain a failure. Confirm output type and requested properties, then inspect the resulting image/video/audio with available tools when relevant. Report unverified properties and distinguish generated output from the source reference.
- Display native tool results or actual returned artifact paths. A seed may help reproducibility when the model supports it; it does not guarantee identical output across revisions.

Use current [fal queue documentation](https://fal.ai/docs/documentation/model-apis/inference/queue) and the selected model's page. Do not add ElevenLabs, VideoDB or another provider to the workflow unless the task explicitly selects and authorizes it.
