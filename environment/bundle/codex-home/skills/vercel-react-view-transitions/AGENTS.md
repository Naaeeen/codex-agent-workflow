# React View Transitions

**Version 1.0.0**
Vercel Engineering
March 2026

> **Note:**
> This document is mainly for agents and LLMs to follow when implementing
> view transitions in React applications. Humans may also find it useful,
> but guidance here is optimized for automation and consistency by
> AI-assisted workflows.

---

## Abstract

Guide for implementing smooth, native-feeling animations using React's View Transition API. Covers the `<ViewTransition>` component, `addTransitionType`, CSS view transition pseudo-elements, shared element transitions, Suspense reveals, list reorder, directional navigation, and Next.js integration. Includes a step-by-step implementation workflow, ready-to-use CSS animation recipes, and common mistake warnings.

---

## Table of Contents

1. [Core Reference](#when-to-animate)
   - [When to Animate](#when-to-animate)
   - [Availability](#availability)
   - [Core Concepts](#core-concepts)
   - [Styling with View Transition Classes](#styling-with-view-transition-classes)
   - [Transition Types](#transition-types)
   - [Shared Element Transitions](#shared-element-transitions)
   - [Common Patterns](#common-patterns)
   - [How Multiple VTs Interact](#how-multiple-vts-interact)
   - [Next.js Integration](#nextjs-integration)
   - [Accessibility](#accessibility)
2. [Implementation Workflow](#implementation-workflow)
   - [Step 1: Audit the App](#step-1-audit-the-app)
   - [Step 2: Add CSS Recipes](#step-2-add-css-recipes)
   - [Step 3: Isolate Persistent Elements](#step-3-isolate-persistent-elements)
   - [Step 4: Add Directional Page Transitions](#step-4-add-directional-page-transitions)
   - [Step 5: Add Suspense Reveals](#step-5-add-suspense-reveals)
   - [Step 6: Add Shared Element Transitions](#step-6-add-shared-element-transitions)
   - [Step 7: Verify Each Navigation Path](#step-7-verify-each-navigation-path)
   - [Common Mistakes](#common-mistakes)
3. [Patterns and Guidelines](#patterns-and-guidelines)
4. [CSS Animation Recipes](#css-animation-recipes)
5. [View Transitions in Next.js](#view-transitions-in-nextjs)

---

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
| **enter** | VT first inserted during a Transition |
| **exit** | VT first removed during a Transition |
| **update** | React DOM changes within the boundary, or its own size/position changing because of an immediate sibling. Nested boundaries own their contained mutations; inspect the boundary's own layout changes separately |
| **share** | Named VT unmounts and another with same `name` mounts in same Transition |

Only `startTransition`, `useDeferredValue`, or `Suspense` activate VTs. Regular `setState` does not animate.

### Critical Placement Rule

For a subtree inserted/removed as one unit, the eligible VT comes before its inserted/removed host nodes. An already-mounted wrapper does not by itself prove that a newly entering child is ineligible:

```jsx
// Works
<ViewTransition enter="auto" exit="auto"><div>Content</div></ViewTransition>

// Broken — div wraps the VT
<div><ViewTransition enter="auto" exit="auto"><div>Content</div></ViewTransition></div>
```

---

## Styling with View Transition Classes

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

---

## Transition Types

Tag transitions with `addTransitionType` so VTs can pick different animations. Call it multiple times to stack types — different VTs in the tree react to different types:

```jsx
startTransition(() => {
  addTransitionType('nav-forward');
  addTransitionType('select-item');
  router.push('/detail/1');
});
```

Map types to CSS classes. Works on `enter`, `exit`, **and** `share`:

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

**TypeScript:** `ViewTransitionClassPerType` requires a `default` key.

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

// Other view — same name
<ViewTransition name="hero-image">
  <img src="/full.jpg" />
</ViewTransition>
```

- Only one VT with a given `name` can be mounted at a time — use unique names. Watch for reusable components: if a component with a named VT is rendered in both a modal/popover *and* a page, both mount simultaneously and break the morph. Either make the name conditional (via a prop) or move the named VT out of the shared component into the specific consumer.
- `share` takes precedence over `enter`/`exit`. Think through each navigation path: when no pair forms, `enter`/`exit` fires instead. Consider whether the element needs a fallback animation for those paths.
- Never use fade-out exit on pages with shared morphs — use directional slide.

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

A boundary can need `update` even when its own content is unchanged: an immediate sibling may move or resize it. Keep that trigger enabled for list reordering and displaced content; see the layout-displacement example in [Patterns and Guidelines](#layout-displacement-morph).

### Composing Shared Elements with List Identity

Shared elements and list identity are independent concerns — don't confuse one for the other. When a list item contains a shared element, use two nested `<ViewTransition>` boundaries:

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

The outer VT handles list reorder/enter. The inner VT handles cross-route shared element morph. Missing either layer means that animation silently doesn't happen.

### Force Re-Enter with `key`

```jsx
<ViewTransition key={searchParams.toString()} enter="slide-up" default="none">
  <ResultsGrid />
</ViewTransition>
```

**Caution:** Wrapping `<Suspense>` with key remounts the boundary and refetches.

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

---

## How Multiple VTs Interact

Every VT matching the trigger fires simultaneously in a single `document.startViewTransition`. VTs in **different** transitions don't compete.

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

See the [View Transitions in Next.js](#view-transitions-in-nextjs) section below.

---

## Accessibility

Always add reduced motion CSS to your global stylesheet:

```css
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(*),
  ::view-transition-new(*),
  ::view-transition-group(*) {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
  }
}
```

---

# Implementation Workflow

Audit the requested flows and use the relevant steps below. Reuse or adapt the needed CSS recipes, preserve the design system, and include reduced-motion behavior.

## Step 1: Audit the App

Before writing any code, scan the codebase thoroughly. Search for:

- **Every `<Link>` and `router.push`** — open every file that contains one
- **Every `<Suspense>` boundary** — check what its fallback renders
- **Every page/route component** — each needs a VT placement decision
- **Persistent elements** (headers, navbars, sidebars) — need `viewTransitionName` isolation
- **Shared visual elements** on both source and target views
- **Skeleton-to-content control pairs** — if a fallback renders a control that also exists in the real content, both need a matching `viewTransitionName`

Then classify every navigation and produce a navigation map:

```
| Route           | Navigates to         | Direction    | VT pattern            |
|-----------------|----------------------|--------------|-----------------------|
| /               | /detail/[id]         | forward      | directional slide     |
| /detail/[id]    | /                    | back         | directional slide     |
| /detail/[id]    | /detail/[other]      | sequential   | directional slide (ordered prev/next) or key+share crossfade |
| /tab/[a]        | /tab/[b]             | lateral      | key+share crossfade   |
| (Suspense)      | (content loads)      | —            | slide-up reveal       |
```

For each shared element (`name` prop), note where a pair forms and where it doesn't — this determines whether you need `enter`/`exit` as a fallback alongside `share`.

## Step 2: Add CSS Recipes

Reuse only the CSS recipes needed by the selected interactions, adapting them to the existing design system. Include reduced-motion behavior.

## Step 3: Isolate Persistent Elements

```jsx
<header style={{ viewTransitionName: "site-header" }}>...</header>
```

```css
::view-transition-group(site-header) {
  animation: none;
  z-index: 100;
}
```

For `backdrop-blur`/`backdrop-filter`, use the backdrop-blur workaround instead.

## Step 4: Add Directional Page Transitions

```jsx
startTransition(() => {
  addTransitionType('nav-forward');
  router.push('/detail/1');
});
```

Wrap each **page component** (not layout) in a type-keyed VT:

```jsx
<ViewTransition
  enter={{ "nav-forward": "nav-forward", "nav-back": "nav-back", default: "none" }}
  exit={{ "nav-forward": "nav-forward", "nav-back": "nav-back", default: "none" }}
  default="none"
>
  <div>...page content...</div>
</ViewTransition>
```

Extract into a reusable component so every page doesn't repeat the type map:

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

**Rules:** Use a quiet type-map fallback for directional navigation where appropriate. Component `default="none"` fits enter/exit-only wrappers; preserve `update`/`share` when wanted. Place route boundaries in participating pages. Use directional slides for hierarchical or ordered navigation.

## Step 5: Add Suspense Reveals

```jsx
<Suspense fallback={<ViewTransition exit="slide-down"><Skeleton /></ViewTransition>}>
  <ViewTransition enter="slide-up" default="none"><AsyncContent /></ViewTransition>
</Suspense>
```

For a content boundary used only for reveal, explicit enter with `default="none"` is appropriate; preserve update/share when also required. Untyped reveals need a string class or a suitable type-map fallback.

## Step 6: Add Shared Element Transitions

```jsx
// Source view
<ViewTransition name={`photo-${photo.id}`} share="morph" default="none">
  <Image src={photo.src} ... />
</ViewTransition>

// Target view — same name
<ViewTransition name={`photo-${photo.id}`} share="morph">
  <Image src={photo.src} ... />
</ViewTransition>
```

When list items contain shared elements, compose both patterns — two independent layers:

```jsx
{items.map(item => (
  <ViewTransition key={item.id}>                                        {/* list identity */}
    <Link href={`/detail/${item.id}`}>
      <ViewTransition name={`item-${item.id}`} share="morph" default="none">  {/* shared element */}
        <Image src={item.image} ... />
      </ViewTransition>
    </Link>
  </ViewTransition>
))}
```

The outer VT handles list reorder/enter. The inner VT handles cross-route shared element morph. Missing either layer means that animation silently doesn't happen.

**Rules:** Names must be unique among simultaneously mounted boundaries. `default="none" share="morph"` is appropriate for a share-only element; keep update on the outer keyed list boundary if it should animate reorder.

## Step 7: Verify Each Navigation Path

Walk through every row in the navigation map from Step 1:

- Does the VT mount/unmount, or stay mounted (same-route)?
- For named VTs: does a shared pair form? If not, does `enter`/`exit` provide a fallback?
- Does `default="none"` block an animation you actually want?
- Do persistent elements stay static?
- Do Suspense reveals animate independently from directional navigations?

---

## Common Mistakes

- **Muting a layout/shared boundary** — `default="none"` disables unspecified update/share; enable the trigger needed by the interaction
- **Directional VT in a layout** — layouts persist, enter/exit won't fire on route changes
- **Fade-out exit with shared morphs** — conflicts with morph, use directional slide
- **Writing custom animation CSS** — use the recipes
- **Confusing defaults** — the type-map `default` selects the unmatched-type fallback; the component `default` supplies unspecified triggers. Either fallback can be a class, auto or none as appropriate
- **Type maps on Suspense reveals** — Suspense resolves have no type, use string props
- **Raw `viewTransitionName` CSS to trigger animations** — React only starts view transitions when `<ViewTransition>` components are in the tree. Bare `viewTransitionName` is for isolating elements, not triggering animations.
- **Assuming a nested boundary disables every outer update** — contained mutations belong to the nested boundary, while the outer boundary may still change layout. Use key/name/share only for an intended identity change
- **Named VT in a reusable component** — if a component with a named VT is rendered in both a modal/popover *and* a page, both mount simultaneously and break the morph. Make the name conditional or move it to the specific consumer.
- **Replacing Back with push just for animation** — push adds a history entry. Keep Back semantics and verify the installed router's transition fallback.

For Next.js-specific steps, see the Next.js section below.

---

# Patterns and Guidelines

## Searchable Grid with `useDeferredValue`

```tsx
'use client';

import { useDeferredValue, useState, ViewTransition, Suspense } from 'react';

export default function SearchableGrid({ itemsPromise }) {
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);

  return (
    <>
      <input value={search} onChange={(e) => setSearch(e.currentTarget.value)} />
      <ViewTransition>
        <Suspense fallback={<GridSkeleton />}>
          <ItemGrid itemsPromise={itemsPromise} search={deferredSearch} />
        </Suspense>
      </ViewTransition>
    </>
  );
}
```

If named elements should only share across routes, `default="none" share="morph"` can suppress their update fades. If those same items should animate filtering/reorder, keep update enabled or use a separate outer keyed boundary.

## Layout Displacement Morph

When a list changes height during a Transition, the following section may move
without changing its own content. An immediate sibling can activate that section's
`update` animation through a size/position change. Give the moving section a boundary
and keep `update` enabled:

```jsx
<>
  <ItemList items={items} />
  <ViewTransition default="none" update="auto">
    <Summary />
  </ViewTransition>
</>
```

This example intentionally opts into layout updates only. A bare boundary is also
appropriate if its other default animations are wanted. Keep stable item keys and
check the actual DOM relationship and Transition timing; merely naming an element
or wrapping an unrelated descendant does not guarantee layout animation.

## Card Expand/Collapse with `startTransition`

```tsx
'use client';

import { useState, useRef, startTransition, ViewTransition } from 'react';

export default function ItemGrid({ items }) {
  const [expandedId, setExpandedId] = useState(null);
  const scrollRef = useRef(0);

  return expandedId ? (
    <ViewTransition enter="slide-in" name={`item-${expandedId}`}>
      <ItemDetail
        item={items.find(i => i.id === expandedId)}
        onClose={() => {
          startTransition(() => {
            setExpandedId(null);
            setTimeout(() => window.scrollTo({ behavior: 'smooth', top: scrollRef.current }), 100);
          });
        }}
      />
    </ViewTransition>
  ) : (
    <div className="grid grid-cols-3 gap-4">
      {items.map(item => (
        <ViewTransition key={item.id} name={`item-${item.id}`}>
          <ItemCard
            item={item}
            onSelect={() => {
              scrollRef.current = window.scrollY;
              startTransition(() => setExpandedId(item.id));
            }}
          />
        </ViewTransition>
      ))}
    </div>
  );
}
```

## Cross-Fade Without Remount

Omit `key` to trigger update (cross-fade) instead of exit + enter. Avoids Suspense remount:

```jsx
<ViewTransition><TabPanel tab={activeTab} /></ViewTransition>
```

## Isolate Elements from Parent Animations

Persistent elements get captured in page's transition snapshot. Fix with `viewTransitionName`:

```jsx
<nav style={{ viewTransitionName: "persistent-nav" }}>{/* ... */}</nav>
```

```css
::view-transition-group(persistent-nav) { animation: none; z-index: 100; }
```

Same for floating elements (popovers, tooltips). Global fix: `::view-transition-group(*) { z-index: 100; }`

## Shared Controls Between Skeleton and Content

Give matching controls the same `viewTransitionName`. Don't put manual `viewTransitionName` on root DOM node inside `<ViewTransition>`.

## Reusable Animated Collapse

```jsx
function AnimatedCollapse({ open, children }) {
  if (!open) return null;
  return <ViewTransition enter="expand-in" exit="collapse-out">{children}</ViewTransition>;
}
```

## Preserve State with Activity

```jsx
<Activity mode={isVisible ? 'visible' : 'hidden'}>
  <ViewTransition enter="slide-in" exit="slide-out"><Sidebar /></ViewTransition>
</Activity>
```

## Exclude Elements with `useOptimistic`

`useOptimistic` values update before snapshot, excluding them from animation. Use for controls; use committed state for animated content.

---

## View Transition Events

Imperative control via `onEnter`, `onExit`, `onUpdate`, `onShare`. Always return cleanup. `onShare` takes precedence.

```jsx
<ViewTransition
  onEnter={(instance, types) => {
    const anim = instance.new.animate(
      [{ transform: 'scale(0.8)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }],
      { duration: 300, easing: 'ease-out' }
    );
    return () => anim.cancel();
  }}
>
  <Component />
</ViewTransition>
```

`instance`: `.old`, `.new`, `.group`, `.imagePair`, `.name`

---

## Animation Timing

| Interaction | Duration |
|------------|----------|
| Direct toggle | 100–200ms |
| Route transition | 150–250ms |
| Suspense reveal | 200–400ms |
| Shared element morph | 300–500ms |

---

## Troubleshooting

Use the installed React/Next.js version and one failing interaction. Identify the
expected trigger before changing keys, defaults, or boundaries.

| Symptom | Checks and focused correction |
|---|---|
| A boundary never animates | Confirm a Transition/Suspense/deferred update and supported browser/runtime. For enter/exit, inspect which subtree is actually inserted/removed; a host node above the boundary can change eligibility. For update, inspect DOM or boundary layout changes instead. |
| A named pair does not morph | Check a matching name on the outgoing and incoming boundary in the same Transition; the target must be rendered for that snapshot. Then inspect `share`, the component `default`, supplied types, and the type-map fallback. `default="none"` without explicit `share` disables the pair. |
| A filtered list or following section jumps | Confirm stable item identity and an eligible `update`; enable `update="auto"` or use a bare boundary when appropriate. For displaced content, inspect the immediate sibling relationship. See [layout displacement](#layout-displacement-morph). |
| Unrelated content cross-fades | Find the boundary whose content/layout actually changed. Disable only the unwanted trigger (for example `update="none"`), or use `default="none"` with every intended trigger enabled explicitly. Do not mute the entire list/shared-element structure indiscriminately. |
| Suspense content appears without a morph | The target may not exist until a later reveal. Use a reveal animation for that later transition or ensure the intended shared target is present; do not add a name to a missing target and assume the pair exists. |
| Only update fires when enter/exit was expected | Check whether identity was retained. Change `key` only for an intended remount/state reset; use update for content/layout changes within stable identity. |
| Nested boundary misses enter/exit | When parent and child are inserted/removed as one unit, the outer eligible boundary can own enter/exit. A nested boundary can still own updates. Inspect the actual subtree instead of assuming every layout wrapper blocks all animation. |
| Same-name error | Use unique names among simultaneously mounted boundaries; inspect reused modal/popover/page components. |
| Back has no directional slide | Preserve history semantics. Untyped traversals use the map fallback; an available shared pair can still morph. See [Next.js guidance](references/nextjs.md). |
| Typed animation does not run | Confirm the navigation supplies the intended type and inspect the map's `default`. Suspense reveals can occur without the earlier navigation type. |

Keep reduced-motion behavior and functional navigation. For backdrop/shape/timing
issues, use the relevant [CSS recipe](references/css-recipes.md) and inspect the real result.
Do not recommend experimental gesture or parent-transition props without verifying
their presence in the installed runtime. A code/config check is not visual E2E proof.

Primary contract: [React ViewTransition](https://react.dev/reference/react/ViewTransition).

---

# CSS Animation Recipes

Ready-to-use CSS for `<ViewTransition>` props. Copy into global stylesheet.

## Timing Variables

```css
:root {
  --duration-exit: 150ms;
  --duration-enter: 210ms;
  --duration-move: 400ms;
}
```

### Shared Keyframes

```css
@keyframes fade {
  from { filter: blur(3px); opacity: 0; }
  to { filter: blur(0); opacity: 1; }
}

@keyframes slide {
  from { translate: var(--slide-offset); }
  to { translate: 0; }
}

@keyframes slide-y {
  from { transform: translateY(var(--slide-y-offset, 10px)); }
  to { transform: translateY(0); }
}
```

## Fade

```css
::view-transition-old(.fade-out) {
  animation: var(--duration-exit) ease-in fade reverse;
}
::view-transition-new(.fade-in) {
  animation: var(--duration-enter) ease-out var(--duration-exit) both fade;
}
```

## Slide (Vertical)

```css
::view-transition-old(.slide-down) {
  animation:
    var(--duration-exit) ease-out both fade reverse,
    var(--duration-exit) ease-out both slide-y reverse;
}
::view-transition-new(.slide-up) {
  animation:
    var(--duration-enter) ease-in var(--duration-exit) both fade,
    var(--duration-move) ease-in both slide-y;
}
```

## Directional Navigation

### Single-Class Approach

```css
::view-transition-old(.nav-forward) {
  --slide-offset: -60px;
  animation:
    var(--duration-exit) ease-in both fade reverse,
    var(--duration-move) ease-in-out both slide reverse;
}
::view-transition-new(.nav-forward) {
  --slide-offset: 60px;
  animation:
    var(--duration-enter) ease-out var(--duration-exit) both fade,
    var(--duration-move) ease-in-out both slide;
}

::view-transition-old(.nav-back) {
  --slide-offset: 60px;
  animation:
    var(--duration-exit) ease-in both fade reverse,
    var(--duration-move) ease-in-out both slide reverse;
}
::view-transition-new(.nav-back) {
  --slide-offset: -60px;
  animation:
    var(--duration-enter) ease-out var(--duration-exit) both fade,
    var(--duration-move) ease-in-out both slide;
}
```

### Separate Enter/Exit Classes

```css
::view-transition-new(.slide-from-right) {
  --slide-offset: 60px;
  animation:
    var(--duration-enter) ease-out var(--duration-exit) both fade,
    var(--duration-move) ease-in-out both slide;
}
::view-transition-old(.slide-to-left) {
  --slide-offset: -60px;
  animation:
    var(--duration-exit) ease-in both fade reverse,
    var(--duration-move) ease-in-out both slide reverse;
}

::view-transition-new(.slide-from-left) {
  --slide-offset: -60px;
  animation:
    var(--duration-enter) ease-out var(--duration-exit) both fade,
    var(--duration-move) ease-in-out both slide;
}
::view-transition-old(.slide-to-right) {
  --slide-offset: 60px;
  animation:
    var(--duration-exit) ease-in both fade reverse,
    var(--duration-move) ease-in-out both slide reverse;
}
```

## Shared Element Morph

```css
::view-transition-group(.morph) {
  animation-duration: var(--duration-move);
}
::view-transition-image-pair(.morph) {
  animation-name: via-blur;
}
@keyframes via-blur {
  30% { filter: blur(3px); }
}
```

**Note:** Shared element transitions take raster snapshots. For text with significant size differences (e.g., `<h3>` → `<h1>`), the old snapshot gets scaled up, producing a visible ghost artifact. Use `text-morph` for text shared elements.

## Text Morph

Avoids raster scaling artifacts on text by hiding the old snapshot and showing the new text at full resolution:

```css
::view-transition-group(.text-morph) {
  animation-duration: var(--duration-move);
}
::view-transition-old(.text-morph) {
  display: none;
}
::view-transition-new(.text-morph) {
  animation: none;
  object-fit: none;
  object-position: left top;
}
```

## Scale

```css
::view-transition-old(.scale-out) {
  animation: var(--duration-exit) ease-in scale-down;
}
::view-transition-new(.scale-in) {
  animation: var(--duration-enter) ease-out var(--duration-exit) both scale-up;
}
@keyframes scale-down {
  from { transform: scale(1); opacity: 1; }
  to { transform: scale(0.85); opacity: 0; }
}
@keyframes scale-up {
  from { transform: scale(0.85); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

## Persistent Element Isolation

```css
::view-transition-group(persistent-nav) {
  animation: none;
  z-index: 100;
}
```

### Backdrop-Blur Workaround

```css
::view-transition-old(persistent-nav) { display: none; }
::view-transition-new(persistent-nav) { animation: none; }
```

## Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(*),
  ::view-transition-new(*),
  ::view-transition-group(*) {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
  }
}
```

---

# View Transitions in Next.js

## Setup

```js
// next.config.js
experimental: { viewTransition: true }
```

Legacy configuration example only: current Next.js documents App Router view transitions without this flag. Check the installed version before adding any configuration; do not install canary automatically.

## Next.js Implementation Additions

**After Step 2:** Check whether the installed version needs a flag; current App Router documentation requires no extra configuration.

**Step 4:** Use `transitionTypes` on `<Link>` (if available — see availability note below):
```tsx
<Link href="/photo/1" transitionTypes={["nav-forward"]}>View</Link>
<Link href="/" transitionTypes={["nav-back"]}>Back</Link>
```

**After Step 6:** For same-route dynamic segments, use `key` + `name` + `share` pattern.

## Layout-Level ViewTransition

Put directional enter/exit wrappers in participating pages because a persistent layout is not re-entered on every navigation. A layout boundary may still serve an intentional update or shared-element purpose. Check which subtree is actually inserted/removed: a persistent parent does not automatically suppress an entering/exiting child. Remove a wrapper only after identifying the unwanted trigger or capture.

## The `transitionTypes` Prop

Works in Server Components, no wrapper needed:
```tsx
<Link href="/products/1" transitionTypes={['nav-forward']}>View</Link>
```

**Availability:** Current Next.js documents this prop, but support differs across releases. Check the installed Link types and matching official docs, then type-check the usage. If unavailable, retain normal Link navigation or use supported programmatic APIs for non-link interactions; do not infer support from the major version alone.

## `loading.tsx` as Suspense Boundary

Next.js `loading.tsx` files are implicit `<Suspense>` boundaries. Wrap the skeleton in `<ViewTransition exit="...">` in `loading.tsx`, and the content in `<ViewTransition enter="..." default="none">` in the page. This is the Next.js-idiomatic equivalent of explicit `<Suspense fallback={...}>`. Same rules apply: use simple string props (not type maps) since Suspense reveals fire without transition types.

## Server-Side Filtering with `router.replace`

For search/sort/filter that re-renders on the server (via URL params), use `startTransition` + `router.replace`. VTs activate because the update is inside `startTransition`. List items wrapped in `<ViewTransition key={item.id}>` animate reorder. This is the server-component alternative to the client-side `useDeferredValue` pattern.

## Two-Layer Pattern (Directional + Suspense)

Directional slides + Suspense reveals coexist because they fire at different moments. Place the directional VT in the **page component** (not layout):

```tsx
<ViewTransition
  enter={{ "nav-forward": "slide-from-right", default: "none" }}
  exit={{ "nav-forward": "slide-to-left", default: "none" }}
  default="none"
>
  <div>
    <Suspense fallback={<ViewTransition exit="slide-down"><Skeleton /></ViewTransition>}>
      <ViewTransition enter="slide-up" default="none"><Content /></ViewTransition>
    </Suspense>
  </div>
</ViewTransition>
```

## Shared Elements Across Routes

```tsx
// List page
<Link href={`/products/${product.id}`} transitionTypes={['nav-forward']}>
  <ViewTransition name={`product-${product.id}`}>
    <Image src={product.image} alt={product.name} width={400} height={300} />
  </ViewTransition>
</Link>

// Detail page — same name
<ViewTransition name={`product-${product.id}`}>
  <Image src={product.image} alt={product.name} width={800} height={600} />
</ViewTransition>
```

## Same-Route Dynamic Segment Transitions

For an intended crossfade between collection content identities, change `key` with the slug while retaining the same shared `name` on both snapshots:

```tsx
<Suspense fallback={<Skeleton />}>
  <ViewTransition key={slug} name="collection-content" share="auto" default="none">
    <Content slug={slug} />
  </ViewTransition>
</Suspense>
```

## Server Components

- `<ViewTransition>` works in Server and Client Components
- `<Link transitionTypes>` works in Server Components
- `addTransitionType` and programmatic nav require Client Components
