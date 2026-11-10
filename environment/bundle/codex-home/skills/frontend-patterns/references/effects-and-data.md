# Effects, async data and debounce

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Custom Hooks Patterns

### State Management Hook

```typescript
export function useToggle(initialValue = false): [boolean, () => void] {
  const [value, setValue] = useState(initialValue)

  const toggle = useCallback(() => {
    setValue(v => !v)
  }, [])

  return [value, toggle]
}

// Usage
const [isOpen, toggleOpen] = useToggle()
```

### Async Data Fetching Hook

Prefer the framework's data loader or the query/cache library already used by the
project. This small hook illustrates client-side loading only: it has no cache,
request deduplication, retries, or server rendering. Keep `fetcher`, `onSuccess`,
and `onError` stable (module functions or `useCallback` with complete dependencies).
An inline options object is fine because the hook depends on its individual values.
Do not suppress dependency linting to hide an unstable callback.

```typescript
interface UseQueryOptions<T> {
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
  enabled?: boolean
}

export function useQuery<T>(
  key: string,
  fetcher: (signal: AbortSignal) => Promise<T>,
  options?: UseQueryOptions<T>
) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(options?.enabled !== false)
  const [revision, setRevision] = useState(0)
  const enabled = options?.enabled !== false
  const onSuccess = options?.onSuccess
  const onError = options?.onError
  const refetch = useCallback(() => setRevision(n => n + 1), [])

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    let ignore = false
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setData(null)

    async function load() {
      try {
        const result = await fetcher(controller.signal)
        if (!ignore) {
          setData(result)
          onSuccess?.(result)
        }
      } catch (cause) {
        if (!ignore) {
          const failure = cause instanceof Error ? cause : new Error(String(cause))
          setError(failure)
          onError?.(failure)
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    void load()
    return () => {
      ignore = true
      controller.abort()
    }
  }, [key, fetcher, enabled, onSuccess, onError, revision])

  return { data, error, loading, refetch }
}

// Stable module-level fetcher; use useCallback when it depends on props/state.
async function fetchMarkets(signal: AbortSignal): Promise<Market[]> {
  const response = await fetch('/api/markets', { signal })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

// Inside a component/custom Hook:
const { data: markets, loading, error, refetch } = useQuery('markets', fetchMarkets)
```

Use cleanup to prevent stale responses from overwriting a later request, including
when the component unmounts. [React's Effect guidance](https://react.dev/reference/react/useEffect#fetching-data-with-effects)
explains the dependency and race-condition requirements.

### Debounce Hook

```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

// Usage
const [searchQuery, setSearchQuery] = useState('')
const debouncedQuery = useDebounce(searchQuery, 500)

useEffect(() => {
  if (debouncedQuery) {
    performSearch(debouncedQuery)
  }
}, [debouncedQuery])
```

## Choosing a loading mechanism

The small hook above has no server rendering, cache, deduplication or retry policy.
Use it only when these omissions are acceptable; otherwise use the established
framework loader or cache. Separate callback failures from transport failures if
callbacks can throw. When disabling or changing a query, define whether previous
data remains visible; loading and stale-data behavior are part of the UI contract.
