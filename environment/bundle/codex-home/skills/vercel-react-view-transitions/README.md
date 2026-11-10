# React View Transitions Skill

An agent skill for implementing smooth, native-feeling animations using React's View Transition API.

## What This Skill Covers

- **`<ViewTransition>` component** — animation triggers (enter, exit, update, share), placement rules, View Transition Classes
- **`addTransitionType`** — tagging transitions for directional or context-specific animations
- **Shared element transitions** — morphing elements across different views
- **View Transition Events** — imperative JavaScript animations via the Web Animations API
- **CSS pseudo-elements** — `::view-transition-old`, `::view-transition-new`, `::view-transition-group`
- **Next.js integration** — version-appropriate setup, the `transitionTypes` prop on `next/link`, App Router patterns
- **Accessibility** — `prefers-reduced-motion` handling
- **Ready-to-use CSS recipes** — fade, slide, scale, directional navigation

## Skill Structure

```
react-view-transitions/
├── SKILL.md                      # Core skill (always loaded)
├── AGENTS.md                     # Full compiled document (all references expanded)
└── references/
    ├── implementation.md         # Step-by-step implementation workflow
    ├── patterns.md               # Patterns, layout displacement, events API
    ├── troubleshooting.md        # Trigger/default/shared-pair diagnostics
    ├── nextjs.md                 # Next.js-specific patterns
    └── css-recipes.md            # Copy-paste CSS animations
```

## Source and Local Adaptation

The maintained source is [vercel-labs/agent-skills, react-view-transitions](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-view-transitions).
This personal copy includes compatibility, scope, and diagnostic corrections.
Compare updates before replacing it; use the available skill installation workflow
only when an installation is requested.

## Resources

- [React `<ViewTransition>` docs](https://react.dev/reference/react/ViewTransition)
- [React `addTransitionType` docs](https://react.dev/reference/react/addTransitionType)
- [Next.js view transitions guide](https://nextjs.org/docs/app/guides/view-transitions)
- [Next.js App Router Playground (view transitions)](https://github.com/vercel/next-app-router-playground/tree/main/app/view-transitions) — Vercel's reference implementation
