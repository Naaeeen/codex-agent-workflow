---
name: vercel-react-view-transitions
description: Guide for implementing smooth, native-feeling animations using React's View Transition API (`ViewTransition` component, `addTransitionType`, and CSS view transition pseudo-elements). Use this skill whenever the user wants to add page transitions, animate route changes, create shared element animations, animate enter/exit of components, animate list reorder, implement directional (forward/back) navigation animations, or integrate view transitions in Next.js. Also use when the user mentions view transitions, `startViewTransition`, `ViewTransition`, transition types, or asks about animating between UI states in React without third-party animation libraries.
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---

# React View Transitions

Animate between UI states using the browser's native `document.startViewTransition`. Declare *what* with `<ViewTransition>`, trigger *when* with `startTransition` / `useDeferredValue` / `Suspense`, control *how* with CSS classes. Unsupported browsers skip animations gracefully.

## When to Animate

Every `<ViewTransition>` should communicate a spatial relationship or continuity. If you can't articulate what it communicates, don't add it.

Choose the patterns that improve the requested interaction. This order can help prioritize them:

| Priority | Pattern | What it communicates |
|----------|---------|---------------------|
| 1 | **Shared element** (`name`) | "Same thing — going deeper" |
| 2 | **Suspense reveal** | "Data loaded" |
| 3 | **List identity** (per-item `key`) | "Same items, new arrangement" |
| 4 | **State change** (`enter`/`exit`) | "Something appeared/disappeared" |
| 5 | **Route change** (page-level) | "Going to a new place" |

Limit changes to the requested flows. A fitting pattern is an option, not a requirement to animate every page or boundary.

### Choosing Animation Style

| Context | Animation | Why |
|---------|-----------|-----|
| Hierarchical navigation (list → detail) | Type-keyed `nav-forward` / `nav-back` | Communicates spatial depth |
| Lateral navigation (tab-to-tab) | Bare `<ViewTransition>` (fade) or `default="none"` | No depth to communicate |
| Suspense reveal | `enter`/`exit` string props | Content arriving |
| Revalidation / background refresh | Disable an unwanted `update`, or explicitly select triggers | Keep desired layout/shared behavior when it carries meaning |

Reserve directional slides for hierarchical navigation (list → detail) and ordered sequences (prev/next photo, carousel, paginated results). For ordered sequences, the direction communicates position: "next" slides from right, "previous" from left. Lateral/unordered navigation (tab-to-tab) should not use directional slides — it falsely implies spatial depth.

---

## Availability

Check the installed React/Next.js versions, exports, and matching official docs
before using these APIs. The current [Next.js guide](https://nextjs.org/docs/app/guides/view-transitions)
documents App Router transitions without extra configuration and without manually
installing React canary. Older releases can have different flags or missing props.
Outside Next.js, verify whether the project's React channel exposes `ViewTransition`
and `addTransitionType`; do not upgrade to canary merely because this skill was loaded.
Check target-browser support for the specific API/CSS features used and preserve
functional navigation when animations are unavailable.

---

## Implementation Workflow

For the requested flows, audit existing behavior using `references/implementation.md`. Reuse or adapt the relevant CSS recipes in `references/css-recipes.md`; preserve the project's design system and include reduced-motion behavior.

---

## Core Concepts

### The `<ViewTransition>` Component

```jsx
import { ViewTransition } from 'react';

<ViewTransition>
  <Component />
</ViewTransition>
```

React auto-assigns a unique `view-transition-name` and calls `document.startViewTransition` behind the scenes. Never call `startViewTransition` yourself.

### Animation Triggers

| Trigger | When it fires |
|---------|--------------|
| **enter** | `<ViewTransition>` first inserted during a Transition |
| **exit** | `<ViewTransition>` first removed during a Transition |
| **update** | React DOM changes within the boundary, or its own size/position changing because of an immediate sibling. Nested boundaries own their contained mutations; inspect the boundary's own layout changes separately |
| **share** | Named VT unmounts and another with same `name` mounts in the same Transition |

Only `startTransition`, `useDeferredValue`, or `Suspense` activate VTs. Regular `setState` does not animate.

### Critical Placement Rule

For a subtree inserted or removed as one unit, the eligible `<ViewTransition>` must come before its inserted/removed host nodes. A host or boundary that was already mounted is a different case; inspect what actually changes in this Transition:

```jsx
// Works
<ViewTransition enter="auto" exit="auto">
  <div>Content</div>
</ViewTransition>

// Broken — div wraps the VT, suppressing enter/exit
<div>
  <ViewTransition enter="auto" exit="auto">
    <div>Content</div>
  </ViewTransition>
</div>
```

---

## Styling with View Transition Classes

### Props

Values: `"auto"` (browser cross-fade), `"none"` (disabled), `"class-name"` (custom CSS), or `{ [type]: value }` for type-specific animations.

```jsx
<ViewTransition default="none" enter="slide-in" exit="slide-out" share="morph" />
```

If `default` is `"none"`, all triggers are off unless explicitly listed.

### CSS Pseudo-Elements

- `::view-transition-old(.class)` — outgoing snapshot
- `::view-transition-new(.class)` — incoming snapshot
- `::view-transition-group(.class)` — container
- `::view-transition-image-pair(.class)` — old + new pair

See `references/css-recipes.md` for ready-to-use animation recipes.

---

## Transition Types

Tag transitions with `addTransitionType` so VTs can pick different animations based on context. Call it multiple times to stack types — different VTs in the tree react to different types:

```jsx
startTransition(() => {
  addTransitionType('nav-forward');
  addTransitionType('select-item');
  router.push('/detail/1');
});
```

Pass an object to map types to CSS classes. Works on `enter`, `exit`, **and** `share`:

```jsx
<ViewTransition
  enter={{ 'nav-forward': 'slide-from-right', 'nav-back': 'slide-from-left', default: 'none' }}
  exit={{ 'nav-forward': 'slide-to-left', 'nav-back': 'slide-to-right', default: 'none' }}
  share={{ 'nav-forward': 'morph-forward', 'nav-back': 'morph-back', default: 'morph' }}
  default="none"
>
  <Page />
</ViewTransition>
```

`enter` and `exit` don't have to be symmetric. For example, fade in but slide out directionally:

```jsx
<ViewTransition
  enter={{ 'nav-forward': 'fade-in', 'nav-back': 'fade-in', default: 'none' }}
  exit={{ 'nav-forward': 'nav-forward', 'nav-back': 'nav-back', default: 'none' }}
  default="none"
>
```

**TypeScript:** `ViewTransitionClassPerType` requires a `default` key in the object.

For apps with multiple pages, extract the type-keyed VT into a reusable wrapper:

```jsx
export function DirectionalTransition({ children }: { children: React.ReactNode }) {
  return (
    <ViewTransition
      enter={{ 'nav-forward': 'nav-forward', 'nav-back': 'nav-back', default: 'none' }}
      exit={{ 'nav-forward': 'nav-forward', 'nav-back': 'nav-back', default: 'none' }}
      default="none"
    >
      {children}
    </ViewTransition>
  );
}
```

### `router.back()` and Browser Back Button

Preserve real history semantics when the user expects Back. A `router.push()` call
adds a new entry and is not an equivalent replacement. Browser back/forward does
not carry the explicit directional types in these examples; a matching shared
element can still animate. Verify the installed router's behavior and provide a
non-directional fallback when appropriate.

### Types and Suspense

Types are available during navigation but **not** during subsequent Suspense reveals (separate transitions, no type). Use type maps for page-level enter/exit; use simple string props for Suspense reveals.

---

## Shared Element Transitions

A pair requires both snapshots in the same Transition. If the incoming target is still behind a Suspense fallback, animate its later reveal separately. With `default="none"`, explicitly set `share="auto"` or a share class; with type-keyed `share`, verify the supplied type and fallback.

Same `name` on two VTs — one unmounting, one mounting — creates a shared element morph:

```jsx
<ViewTransition name="hero-image">
  <img src="/thumb.jpg" onClick={() => startTransition(() => onSelect())} />
</ViewTransition>

// On the other view — same name
<ViewTransition name="hero-image">
  <img src="/full.jpg" />
</ViewTransition>
```

- Only one VT with a given `name` can be mounted at a time — use unique names (`photo-${id}`). Watch for reusable components: if a component with a named VT is rendered in both a modal/popover *and* a page, both mount simultaneously and break the morph. Either make the name conditional (via a prop) or move the named VT out of the shared component into the specific consumer.
- `share` takes precedence over `enter`/`exit`. Think through each navigation path: when no matching pair forms (e.g., the target page doesn't have the same name), `enter`/`exit` fires instead. Consider whether the element needs a fallback animation for those paths.
- Never use a fade-out exit on pages with shared morphs — use a directional slide instead.

---

## Common Patterns

### Enter/Exit

```jsx
{show && (
  <ViewTransition enter="fade-in" exit="fade-out"><Panel /></ViewTransition>
)}
```

### List Reorder

```jsx
{items.map(item => (
  <ViewTransition key={item.id}><ItemCard item={item} /></ViewTransition>
))}
```

Trigger inside `startTransition`. Avoid wrapper `<div>`s between list and VT.

### Layout Changes from Siblings

A boundary can need `update` even when its own content is unchanged: an immediate sibling may move or resize it. Keep that trigger enabled for list reordering and displaced content; see the layout-displacement example in [references/patterns.md](references/patterns.md#layout-displacement-morph).

### Composing Shared Elements with List Identity

Shared elements and list identity are independent concerns — don't confuse one for the other. When a list item contains a shared element (e.g., an image that morphs into a detail view), use two nested `<ViewTransition>` boundaries:

```jsx
{items.map(item => (
  <ViewTransition key={item.id}>                                      {/* list identity */}
    <Link href={`/items/${item.id}`}>
      <ViewTransition name={`item-image-${item.id}`} share="morph">   {/* shared element */}
        <Image src={item.image} />
      </ViewTransition>
      <p>{item.name}</p>
    </Link>
  </ViewTransition>
))}
```

The outer VT handles list reorder/enter animations. The inner VT handles the cross-route shared element morph. Missing either layer means that animation silently doesn't happen.

### Force Re-Enter with `key`

```jsx
<ViewTransition key={searchParams.toString()} enter="slide-up" default="none">
  <ResultsGrid />
</ViewTransition>
```

**Caution:** If wrapping `<Suspense>`, changing `key` remounts the boundary and refetches.

### Suspense Fallback to Content

Simple cross-fade:
```jsx
<ViewTransition>
  <Suspense fallback={<Skeleton />}><Content /></Suspense>
</ViewTransition>
```

Directional reveal:
```jsx
<Suspense fallback={<ViewTransition exit="slide-down"><Skeleton /></ViewTransition>}>
  <ViewTransition enter="slide-up" default="none"><Content /></ViewTransition>
</Suspense>
```

For more patterns, see `references/patterns.md`.

---

## How Multiple VTs Interact

Every VT matching the trigger fires simultaneously in a single `document.startViewTransition`. VTs in **different** transitions (navigation vs later Suspense resolve) don't compete.

### Choose Defaults for the Boundary's Job

An unchanged boundary does not animate just because another transition runs.
For a boundary that activates, the component's `default` prop supplies the class
for triggers without an explicit prop. Setting it to `"none"` also disables an
unspecified `update` and `share`; use it deliberately.

| Intended behavior | Configuration | Consequence |
|---|---|---|
| Enter/exit only | `default="none" enter="fade-in" exit="fade-out"` | Updates and shared pairs stay off |
| List reorder or sibling-driven layout movement only | `default="none" update="auto"` | Keeps layout animation; add enter/exit if list insertion/removal should animate too |
| Shared pair only | `default="none" share="morph"` | Matching names still morph; ordinary updates stay off |
| All applicable browser-default animations | Bare `<ViewTransition>` | Keeps the default behavior for each trigger that actually activates |
| Suppress updates but retain other defaults | `update="none"` | Does not implicitly disable enter/exit/share |

The `default` entry *inside a type map* is a different fallback: it chooses a class
when no supplied transition type matches. `default: "none"` is useful for directional
navigation that should stay quiet on untyped updates; it is not required for every
map. A shared pair with a type-keyed `share` needs the expected type or a suitable
map fallback. Check both kinds of default when an animation disappears.

### Two Patterns Coexist

**Pattern A — Directional slides:** Type-keyed VT on each page, fires during navigation.
**Pattern B — Suspense reveals:** Simple string props, fires when data loads (no type).

Use `default="none"` with explicit enter/exit for boundaries whose only job is directional navigation or a reveal. Keep or explicitly enable `update` and `share` on boundaries that also need layout or shared-element animation. Place directional route boundaries in the participating pages and evaluate enter/exit independently.

### Nested VT Limitation

When a parent and its nested boundaries enter or exit as one inserted/removed subtree, the outer eligible boundary owns that enter/exit. If the parent persists and only a child is inserted/removed, diagnose the child's actual eligibility instead of assuming nesting disables it. Nested updates and shared pairs are separate triggers; verify any newer opt-in props against the installed runtime.

---

## Next.js Integration

For version-specific Next.js setup, `transitionTypes`, App Router patterns and Server Components, see `references/nextjs.md`.

---

## Accessibility

Always add the reduced motion CSS from `references/css-recipes.md` to your global stylesheet.

---

## Reference Files

- **`references/implementation.md`** — Step-by-step implementation workflow.
- **`references/patterns.md`** — Patterns, layout displacement, animation timing and events API.
- **[references/troubleshooting.md](references/troubleshooting.md)** — Missing update/share animations, unexpected fades and boundary diagnosis.
- **`references/css-recipes.md`** — Ready-to-use CSS animation recipes.
- **`references/nextjs.md`** — Next.js App Router patterns and Server Component details.

## Full Compiled Document

For the compiled core and examples, including diagnostic guidance: `AGENTS.md`. Prefer the focused reference needed for the current task.
