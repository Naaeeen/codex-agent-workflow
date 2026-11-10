---
name: frontend-design
description: "Design and implement a distinctive web interface when the user requests a new visual direction, polished page, landing page, or substantial UI styling. Respect the existing design system for product changes; do not trigger for non-visual maintenance or unrelated document/poster work."
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Thinking

Before coding, inspect the existing interface, design system, framework, and user intent. Preserve them for scoped product changes; choose a distinct direction when creating a new design or when a redesign is requested:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Select a tone suited to the audience; possible directions include brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Preserve established brand fonts and check language coverage, loading cost, and readability. For a new identity, consider a characterful display font paired with a readable body font; common and system fonts remain valid when they fit the project.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use motion only when it supports the task, preserve keyboard/focus behavior, and respect reduced-motion preferences. Provide pause/stop controls for applicable automatic movement; do not make content access depend on animation.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, and grain overlays when they remain accessible and performant.

Avoid an arbitrary template that ignores the context. Established fonts, familiar components, centered layouts, and any brand color can be appropriate; judge the composition by usability and the requested identity.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary new concepts where it serves the brief; keep related product screens coherent rather than changing themes or fonts merely for novelty.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Before delivery, verify the affected interaction and layout in an available browser at relevant viewport sizes. Report any check that could not be run; visual intent alone does not establish production readiness.
