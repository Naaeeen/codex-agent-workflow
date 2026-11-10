# Identity, authorization and sessions

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

## Credential storage follows the client

- **Browser application:** prefer a backend-held session or token with an
  appropriately scoped `HttpOnly; Secure` cookie when the architecture supports
  it. Set `SameSite` for the real sign-in/navigation/embedding flow and apply CSRF
  controls. Avoid persisting credentials in localStorage/sessionStorage because
  origin JavaScript can read them. If the established design requires browser-
  held bearer tokens, keep lifetime/exposure minimal and document the XSS risks;
  memory isolation does not make XSS harmless.
- **Native application:** browser cookie rules do not replace platform credential
  storage. Use the selected platform's supported protected store, such as Apple
  Keychain or encryption keys held by Android Keystore protecting app-private
  credential data. Verify backup, access-group and device-lock behavior; Keystore
  stores keys, not an arbitrary token string. Avoid ordinary preferences/files.
- **Server/workload:** use the existing scoped secret store or workload identity.
  Never place a server credential in client bundles or URLs.

`HttpOnly` reduces script access to cookies but does not stop injected script
from acting as the user. Storage choice also needs expiry, rotation/revocation,
logout semantics and transport protection. Do not replace the project's session
architecture without a concrete requirement.

Sources checked 2026-11-05: [OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[Apple Keychain](https://developer.apple.com/documentation/security/keychain-services),
[Android Keystore](https://developer.android.com/privacy-and-security/keystore).

## Authentication and access checks

- Validate signatures/credentials and applicable issuer, audience, algorithm,
  expiry and token-purpose rules with the established provider; validate claim
  shapes after cryptographic validation. Do not cast arbitrary decoded claims
  into a trusted user type. See [JWT BCP](https://www.rfc-editor.org/rfc/rfc8725.html).
- Preserve one internal principal shape. Requester IDs, role fields and tenant IDs
  in the request are untrusted unless separately authorized for that action.
- Check action plus resource/tenant scope. Role checks alone are insufficient.
  Protect reads as well as writes, field updates and related-object access.
- Test no credential, invalid/expired credential, wrong role, another user's
  resource, another tenant and the valid owner/admin path as applicable.
- For Supabase RLS, read the dedicated skill and test actual roles/policies,
  including insert/update checks and service-role behavior. The previous two
  generic SELECT/UPDATE policies were not a complete deployment policy.


### 6. CSRF Protection

Choose protection from the authentication model. Browser requests authenticated by
automatically attached cookies need CSRF defenses on state-changing operations.
Use the framework's built-in protection or a correctly validated synchronizer token;
a signed double-submit cookie is an alternative for suitable stateless designs,
not an additional universal requirement. Do not implement a home-grown token scheme.

`SameSite` is defense in depth. Choose `Lax`, `Strict`, or `None; Secure` according
to actual navigation, cross-site embedding, and sign-in flows; `Strict` on every
cookie can break legitimate flows. An API that exclusively accepts an explicitly
set Authorization header has a different CSRF surface, but still needs correct CORS
and XSS defenses. Verify there is no cookie-authentication fallback.

#### Verification Steps
- [ ] The authentication transport and cookie behavior are understood
- [ ] State changes use appropriate methods; GET/HEAD do not mutate state
- [ ] Cross-origin attempts and missing/invalid CSRF tokens are rejected where applicable
- [ ] SameSite and Origin/Referer checks match legitimate sign-in and embedded flows
- [ ] The framework's CSRF protection or one verified token pattern is used correctly

See [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

## Focused session evidence

Check actual credential transport, cookie attributes, cross-origin rejection,
expiry and logout/revocation behavior. A passing happy-path login does not prove
that cross-site writes or stale tokens are rejected.
