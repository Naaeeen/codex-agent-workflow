# View Transitions in Next.js

## Setup

First check the installed Next.js version and its [official view-transition guide](https://nextjs.org/docs/app/guides/view-transitions).
The current App Router guide documents view transitions with no configuration and
no separate React canary install. Older releases may require an experimental flag
or lack some APIs. Do not add `experimental.viewTransition` or change React versions
without confirming that the installed release requires it.

---

## Next.js Implementation Additions

When following `implementation.md`, apply these additions:

**After Step 2:** Apply only the setup required by the installed version.

**Step 4:** Use `transitionTypes` on `<Link>` — see "The `transitionTypes` Prop" section below for usage and availability.

**After Step 6:** For same-route dynamic segments (e.g., `/collection/[slug]`), use the `key` + `name` + `share` pattern — see Same-Route Dynamic Segment Transitions below.

---

## Layout-Level ViewTransition

Put directional enter/exit wrappers in participating pages: a persistent layout
does not re-enter on every route change. A layout boundary can still have an
intentional update or shared-element role.

Inspect the subtree inserted/removed in this Transition. If parent and child
enter/exit together, the outer eligible boundary owns that trigger. If the parent
persists and only the child changes, nesting alone does not prove the child's
enter/exit is blocked. Remove a wrapper only after identifying its unwanted
trigger or capture, rather than applying a blanket layout ban.

## The `transitionTypes` Prop on `next/link`

No wrapper component needed, works in Server Components:

```tsx
<Link href="/products/1" transitionTypes={['transition-to-detail']}>View Product</Link>
```

Replaces the manual pattern of `onNavigate` + `startTransition` + `addTransitionType` + `router.push()`. Reserve manual `startTransition` for non-link interactions (buttons, forms).

**Availability:** Current Next.js documents `transitionTypes` on Link, but do not
infer support from "Next.js 16+" alone. Check the installed Link types and matching
official docs, then type-check. If absent, preserve ordinary Link navigation;
use supported programmatic APIs for non-link interactions instead of forcing an upgrade.

Call `useRouter()` at the top level of a Client Component or custom Hook, never inside the event handler. See [React Rules of Hooks](https://react.dev/reference/rules/rules-of-hooks) and [Next.js useRouter](https://nextjs.org/docs/app/api-reference/functions/use-router). Only pass trusted local destinations to these examples.

## Programmatic Navigation

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { startTransition, addTransitionType } from 'react';

export function DetailButton({ href }: { href: string }) {
  const router = useRouter();
  function handleNavigate() {
    startTransition(() => {
      addTransitionType('nav-forward');
      router.push(href);
    });
  }
  return <button onClick={handleNavigate}>View details</button>;
}
```

---

## Server-Side Filtering with `router.replace`

For search/sort/filter that re-renders on the server (via URL params), use `startTransition` + `router.replace`. VTs activate because the state update is inside `startTransition`:

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { startTransition } from 'react';

export function SortButton({ sort }: { sort: string }) {
  const router = useRouter();
  function handleSort() {
    startTransition(() => {
      const params = new URLSearchParams(window.location.search);
      params.set('sort', sort);
      router.replace(`${window.location.pathname}?${params}${window.location.hash}`);
    });
  }
  return <button onClick={handleSort}>Apply sort</button>;
}
```

List items wrapped in `<ViewTransition key={item.id}>` will animate reorder. This is the server-component alternative to the client-side `useDeferredValue` pattern in `patterns.md`.

---

The enter/exit-only examples below intentionally disable other triggers on those wrappers. If the same boundary also needs layout updates or shared pairs, explicitly retain update/share; see [troubleshooting.md](troubleshooting.md).

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

---

## `loading.tsx` as Suspense Boundary

Next.js `loading.tsx` is an implicit `<Suspense>` boundary. Wrap the skeleton in `<ViewTransition exit="...">` in `loading.tsx`, and the content in `<ViewTransition enter="..." default="none">` in the page:

```tsx
// loading.tsx
<ViewTransition exit="slide-down"><PhotoGridSkeleton /></ViewTransition>

// page.tsx
<ViewTransition enter="slide-up" default="none"><PhotoGrid photos={photos} /></ViewTransition>
```

Same rules as explicit `<Suspense>`: use simple string props (not type maps) since Suspense reveals fire without transition types.

---

## Shared Elements Across Routes

```tsx
// List page
{products.map((product) => (
  <Link key={product.id} href={`/products/${product.id}`} transitionTypes={['nav-forward']}>
    <ViewTransition name={`product-${product.id}`}>
      <Image src={product.image} alt={product.name} width={400} height={300} />
    </ViewTransition>
  </Link>
))}

// Detail page — same name
<ViewTransition name={`product-${product.id}`}>
  <Image src={product.image} alt={product.name} width={800} height={600} />
</ViewTransition>
```

---

## Same-Route Dynamic Segment Transitions

For an intended content-identity change within a route such as `/collection/[slug]`, use a changing `key` with a stable shared `name`. The old and new content containers need the same name to form a pair:

```tsx
<Suspense fallback={<Skeleton />}>
  <ViewTransition key={slug} name="collection-content" share="auto" default="none">
    <Content slug={slug} />
  </ViewTransition>
</Suspense>
```

- `key={slug}` forces unmount/remount on change
- The stable `name="collection-content"` pairs the two snapshots; `share="auto"` enables the crossfade. Keep distinct names on independently mounted items; do not give every collection the same name if several are visible simultaneously
- VT inside `<Suspense>` (without keying Suspense) keeps old content visible during loading

---

## Server Components

- `<ViewTransition>` works in both Server and Client Components
- `<Link transitionTypes>` works in Server Components — no `'use client'` needed
- `addTransitionType` and `startTransition` for programmatic nav require Client Components
