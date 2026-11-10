# Troubleshooting

Use the installed React/Next.js version and one failing interaction. Identify the
expected trigger before changing keys, defaults, or boundaries.

| Symptom | Checks and focused correction |
|---|---|
| A boundary never animates | Confirm a Transition/Suspense/deferred update and supported browser/runtime. For enter/exit, inspect which subtree is actually inserted/removed; a host node above the boundary can change eligibility. For update, inspect DOM or boundary layout changes instead. |
| A named pair does not morph | Check a matching name on the outgoing and incoming boundary in the same Transition; the target must be rendered for that snapshot. Then inspect `share`, the component `default`, supplied types, and the type-map fallback. `default="none"` without explicit `share` disables the pair. |
| A filtered list or following section jumps | Confirm stable item identity and an eligible `update`; enable `update="auto"` or use a bare boundary when appropriate. For displaced content, inspect the immediate sibling relationship. See [layout displacement](patterns.md#layout-displacement-morph). |
| Unrelated content cross-fades | Find the boundary whose content/layout actually changed. Disable only the unwanted trigger (for example `update="none"`), or use `default="none"` with every intended trigger enabled explicitly. Do not mute the entire list/shared-element structure indiscriminately. |
| Suspense content appears without a morph | The target may not exist until a later reveal. Use a reveal animation for that later transition or ensure the intended shared target is present; do not add a name to a missing target and assume the pair exists. |
| Only update fires when enter/exit was expected | Check whether identity was retained. Change `key` only for an intended remount/state reset; use update for content/layout changes within stable identity. |
| Nested boundary misses enter/exit | When parent and child are inserted/removed as one unit, the outer eligible boundary can own enter/exit. A nested boundary can still own updates. Inspect the actual subtree instead of assuming every layout wrapper blocks all animation. |
| Same-name error | Use unique names among simultaneously mounted boundaries; inspect reused modal/popover/page components. |
| Back has no directional slide | Preserve history semantics. Untyped traversals use the map fallback; an available shared pair can still morph. See [Next.js guidance](nextjs.md). |
| Typed animation does not run | Confirm the navigation supplies the intended type and inspect the map's `default`. Suspense reveals can occur without the earlier navigation type. |

Keep reduced-motion behavior and functional navigation. For backdrop/shape/timing
issues, use the relevant [CSS recipe](css-recipes.md) and inspect the real result.
Do not recommend experimental gesture or parent-transition props without verifying
their presence in the installed runtime. A code/config check is not visual E2E proof.

Primary contract: [React ViewTransition](https://react.dev/reference/react/ViewTransition).
