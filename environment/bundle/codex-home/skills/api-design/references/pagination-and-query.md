# Pagination, filtering and ordering

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Pagination

### Offset-Based (Simple)

```
GET /api/v1/users?page=2&per_page=20

# Implementation
SELECT * FROM users
ORDER BY created_at DESC
LIMIT 20 OFFSET 20;
```

**Pros:** Easy to implement, supports "jump to page N"
**Cons:** Slow on large offsets (OFFSET 100000), inconsistent with concurrent inserts

### Cursor-Based (Scalable)

```
GET /api/v1/users?cursor=eyJpZCI6MTIzfQ&limit=20

# Implementation
SELECT * FROM users
WHERE id > :cursor_id
ORDER BY id ASC
LIMIT 21;  -- fetch one extra to determine has_next
```

```json
{
  "data": [...],
  "meta": {
    "has_next": true,
    "next_cursor": "eyJpZCI6MTQzfQ"
  }
}
```

**Pros:** Avoids scanning large offsets with a suitable index; can reduce duplicate/skipped rows for the chosen ordering
**Cons:** No arbitrary page jump; changing sort keys or concurrent updates still need a consistency policy

### Choosing a collection contract

Use offset when page-number navigation matters and the expected query cost is
acceptable; use keyset/cursor when sequential navigation and indexed continuation
fit the caller. Size thresholds alone do not determine the choice.

Use a deterministic unique order (for example, timestamp plus ID) and encode all
continuation fields in the cursor. Validate cursor structure, bind it to its query
scope, and retain server-side authorization. An opaque/base64 cursor is not an
authorization mechanism or an encrypted secret. Define page-size caps, empty
pages, invalid/expired cursors and concurrent-change semantics.

## Filtering, Sorting, and Search

### Filtering

```
# Simple equality
GET /api/v1/orders?status=active&customer_id=abc-123

# Comparison operators (use bracket notation)
GET /api/v1/products?price[gte]=10&price[lte]=100
GET /api/v1/orders?created_at[after]=2025-01-01

# Multiple values (comma-separated)
GET /api/v1/products?category=electronics,clothing

# Nested fields (dot notation)
GET /api/v1/orders?customer.country=US
```

### Sorting

```
# Single field (prefix - for descending)
GET /api/v1/products?sort=-created_at

# Multiple fields (comma-separated)
GET /api/v1/products?sort=-featured,price,-created_at
```

### Full-Text Search

```
# Search query parameter
GET /api/v1/products?q=wireless+headphones

# Field-specific search
GET /api/v1/users?email=alice
```

### Sparse Fieldsets

```
# Return only specified fields (reduces payload)
GET /api/v1/users?fields=id,name,email
GET /api/v1/orders?fields=id,total,status&include=customer.name
```

Allowlist filter/sort/projection fields and operators; enforce type and complexity
limits. Parameterize values and map allowed sort fields to known identifiers.
Reject unsupported combinations clearly. Sparse fields and includes may not
expose properties or related records beyond the caller's access scope.
