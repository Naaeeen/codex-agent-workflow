# Untrusted input, storage and rendering

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

### 2. Input Validation

#### Validate at the receiving boundary

Choose bounds from the actual domain. The source's age field is an illustration,
not a required user property or permission to collect it. Restrict writable
properties and distinguish malformed input from domain validation failure.
```typescript
import { z } from 'zod'

// Define validation schema
const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().min(0).max(150)
})

// Validate before processing
export async function createUser(input: unknown) {
  try {
    const validated = CreateUserSchema.parse(input)
    return await db.users.create(validated)
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { success: false, errors: error.issues }
    }
    throw error
  }
}
```

#### File Upload Validation

Client MIME types, extensions, and signatures alone do not establish safe content.
Enforce the request-body limit before buffering. Authorize uploads to the target,
then use the project's maintained decoder to validate and re-encode actual bytes.
The following is an application boundary contract, not a drop-in decoder:

```typescript
interface ImageUploadChecks {
  // Read the authenticated principal from trusted server context, not a request ID.
  authorizeTarget(targetId: string): Promise<void>
  // Reject malformed/unsupported input; enforce pixel/frame/memory limits while
  // decoding, and return a fresh JPEG/PNG without untrusted embedded metadata.
  decodeAndReencode(bytes: Uint8Array, limits: {
    maxPixels: number; maxFrames: number
  }): Promise<{ bytes: Uint8Array; format: 'jpeg' | 'png' }>
}

async function validateImageUpload(file: File, targetId: string, checks: ImageUploadChecks) {
  await checks.authorizeTarget(targetId)
  const maxBytes = 5 * 1024 * 1024
  if (file.size <= 0 || file.size > maxBytes) throw new Error('Invalid file size')
  const bytes = new Uint8Array(await file.arrayBuffer())
  if (bytes.byteLength === 0 || bytes.byteLength > maxBytes) throw new Error('Invalid file size')
  const image = await checks.decodeAndReencode(bytes, { maxPixels: 20_000_000, maxFrames: 1 })
  if (!['jpeg', 'png'].includes(image.format)) throw new Error('Unsupported decoded format')
  if (image.bytes.byteLength === 0 || image.bytes.byteLength > maxBytes) throw new Error('Invalid output size')
  return { bytes: image.bytes, storageName: `${crypto.randomUUID()}.${image.format}` }
}
```

Store outside an executable web root or in a private bucket with download authorization;
set a trusted content type and suitable `Content-Disposition`. Add malware scanning or
content disarm when the accepted formats and threat model require it. Do not send private
uploads to public scanning services without authorization.
See [OWASP upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

#### Verification Steps
- [ ] Schemas validate input at the server boundary
- [ ] Upload tests cover unauthorized targets, spoofed MIME/extension, malformed content, empty/oversize files, and decoder resource limits
- [ ] Storage and download permissions match the intended audience
- [ ] No direct use of user input in queries
- [ ] Validation errors expose only appropriate field details

### 3. SQL Injection Prevention

#### FAIL: NEVER Concatenate SQL
```typescript
// DANGEROUS - SQL Injection vulnerability
const query = `SELECT * FROM users WHERE email = '${userEmail}'`
await db.query(query)
```

#### PASS: ALWAYS Use Parameterized Queries
```typescript
// Safe - parameterized query
// Use the dedicated provider skill for query-builder and row-policy details.
await db.query(
  'SELECT * FROM users WHERE email = $1',
  [userEmail]
)
```

#### Verification Steps
- [ ] All database queries use parameterized queries
- [ ] No string concatenation in SQL
- [ ] ORM/query builder used correctly
- [ ] Query-builder/operator inputs and SQL identifiers are allowlisted; values are bound

### 5. XSS Prevention

#### Output depends on context

Render untrusted strings as text by default. HTML sanitization is only for a
feature that deliberately accepts HTML; it does not make a string safe for URL,
script, CSS or arbitrary attribute contexts. Configure and maintain the chosen
sanitizer and verify the actual rendering path.
```typescript
import DOMPurify from 'isomorphic-dompurify'

// When HTML rendering is required, sanitize for the intended HTML context
function renderUserContent(html: string) {
  const clean = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p'],
    ALLOWED_ATTR: []
  })
  return <div dangerouslySetInnerHTML={{ __html: clean }} />
}
```

#### Content Security Policy

Do not make `unsafe-inline` or `unsafe-eval` the production script policy. Use the
framework's nonce or hash integration and verify all required scripts still work.
For nonce-based Next.js rendering, generate an unpredictable nonce per request,
propagate the CSP/nonce to the framework request and response, and attach it to
authorized inline scripts. A static `next.config.js` header cannot implement that
per-request lifecycle by itself.

Example **policy shape**, not a complete Next.js integration:

```typescript
function productionCsp(nonce: string) {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'"
  ].join('; ')
}
```

The nonce must be generated by the server and validated as a safe nonce value, not
accepted from user input. Adapt resource origins and embedding rules to the app.
Nonce-based rendering affects caching/static rendering; consider supported hash/SRI
approaches where appropriate. Apply development-only exceptions only to development.
Follow the installed version's [Next.js CSP guide](https://nextjs.org/docs/app/guides/content-security-policy)
and test hydration, navigation, third-party scripts, and CSP violation reports.

#### Verification Steps
- [ ] User-provided HTML sanitized
- [ ] CSP headers configured
- [ ] No unvalidated dynamic content rendering
- [ ] React's built-in XSS protection used
