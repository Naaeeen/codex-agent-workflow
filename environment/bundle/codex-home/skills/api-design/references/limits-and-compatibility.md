# Rate-limit responses and compatibility

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Rate Limiting

### Headers

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000

# When exceeded
HTTP/1.1 429 Too Many Requests
Retry-After: 60
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 60 seconds."
  }
}
```

### Rate Limit Tiers

Illustrative capacity numbers only. Set actual budgets from operation cost,
service capacity and abuse risk; IP is only usable through a trusted proxy setup.
These legacy `X-RateLimit-*` names are an example existing contract, not a claim
that every platform emits them. Verify the chosen provider's current headers.

| Tier | Limit | Window | Use Case |
|------|-------|--------|----------|
| Anonymous | 30/min | Per IP | Public endpoints |
| Authenticated | 100/min | Per user | Standard API access |
| Premium | 1000/min | Per API key | Paid API plans |
| Internal | 10000/min | Per service | Service-to-service |

## Versioning

### URL Path Versioning

```
/api/v1/users
/api/v2/users
```

**Pros:** Explicit, easy to route, cacheable
**Cons:** URL changes between versions

### Header Versioning

```
GET /api/users
Accept: application/vnd.myapp.v2+json
```

**Pros:** Clean URLs
**Cons:** Harder to test, easy to forget

### Compatibility strategy

Choose URL/header versioning to fit the existing API and clients. Define supported
versions, deprecation notice, migration window and retirement behavior from the
actual commitment; two active versions or six months are not universal rules.

Removing/renaming fields, changing field types, access semantics or URL structure
can break callers. Additions can also break strict schemas or exhaustive enum
handling. Validate representative clients, document the migration, and set a
`Sunset` header only for an agreed retirement date. Use an appropriate retired-
resource response for the agreed policy; do not automatically return 410 for
every old API version.
