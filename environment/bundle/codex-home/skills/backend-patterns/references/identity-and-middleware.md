# Identity and middleware contracts

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## One internal principal

Use one shape after authentication. The former `JWTPayload.userId` plus `User.id`
and different role unions could not safely satisfy the same middleware contract.
The illustrative types below use `Principal.id` and one `Role` everywhere.

```typescript
type Role = 'admin' | 'moderator' | 'user'
type Permission = 'read' | 'write' | 'delete' | 'admin'

interface Principal {
  readonly id: string
  readonly role: Role
}

type Authenticate = (request: Request) => Promise<Principal>
type AuthenticatedHandler =
  (request: Request, principal: Principal) => Promise<Response>

const permissions: Record<Role, readonly Permission[]> = {
  admin: ['read', 'write', 'delete', 'admin'],
  moderator: ['read', 'write', 'delete'],
  user: ['read', 'write']
}

function hasPermission(principal: Principal, permission: Permission): boolean {
  return permissions[principal.role].includes(permission)
}
```

These types and the permission table describe handoff, not an authentication
implementation. Permission names and grants are examples; apply the real policy,
including resource ownership and tenant scope, before reads or mutations.

## Adapter contract

1. The project's authenticator extracts the supported credential transport and
   verifies it using maintained provider/library code. A TypeScript assertion on
   `jwt.verify` output does not validate a claim schema.
2. Verify the configured algorithm/key and applicable issuer, audience, expiry,
   not-before and token-purpose rules; validate required claim types and allowed
   role values. Map verified subject to `Principal.id` once. Do not trust a role
   or requester ID from request JSON.
3. Return or pass `Principal` only on success; distinguish missing/invalid
   authentication from a verified principal lacking permission.
4. Catch credential failures at the authenticator boundary. Do not catch handler
   bugs or database errors and misreport all of them as invalid credentials.
5. Apply current resource/tenant authorization in the use case; a global role
   predicate alone does not authorize every record.

Use `security-review` for the affected authentication/session boundary, and
[RFC 8725](https://www.rfc-editor.org/rfc/rfc8725.html) for JWT validation principles.
Provider-specific session APIs belong to their installed skills. No custom
`verifyToken`, assumed request augmentation or complete JWT adapter is supplied.
