# Secrets, diagnostics and dependency checks

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

### 1. Secrets Management

#### FAIL: NEVER Do This
```typescript
const apiKey = "DEMO_KEY"  // Illustrative hardcoded value
const dbPassword = "password123" // In source code
```

#### Example: an injected server secret

Use the existing secret manager or workload identity. Environment injection is
one server-side option; do not expose the value in a browser bundle or logs.
```typescript
const apiKey = process.env.OPENAI_API_KEY
const dbUrl = process.env.DATABASE_URL

// Verify secrets exist
if (!apiKey) {
  throw new Error('OPENAI_API_KEY not configured')
}
```

#### Verification Steps
- [ ] No hardcoded API keys, tokens, or passwords
- [ ] Secrets use the project's approved store/workload identity; environment injection is one option
- [ ] `.env.local` in .gitignore
- [ ] Check the changed diff and relevant history for accidental secrets; escalate actual exposure for authorized rotation
- [ ] Production secrets in hosting platform (Vercel, Railway)

### 8. Sensitive Data Exposure

#### Logging
```typescript
// FAIL: WRONG: Logging sensitive data
console.log('User login:', { email, password })
console.log('Payment:', { cardNumber, cvv })

// PASS: CORRECT: Redact sensitive data
console.log('User login:', { event: 'login.completed', requestId })
console.log('Payment:', { event: 'payment.completed', requestId })
```

#### Error Messages
```typescript
// FAIL: WRONG: Exposing internal details
catch (error) {
  return NextResponse.json(
    { error: error.message, stack: error.stack },
    { status: 500 }
  )
}

// PASS: CORRECT: Generic error messages
catch (error) {
  // Record only approved redacted diagnostics with a correlation ID.
  return NextResponse.json(
    { error: 'An error occurred. Please try again.' },
    { status: 500 }
  )
}
```

#### Verification Steps
- [ ] No passwords, tokens, or secrets in logs
- [ ] Error messages generic for users
- [ ] Internal diagnostics are redacted and access-controlled; raw error objects may contain secrets
- [ ] No stack traces exposed to users

### 10. Dependency Security

Do not install monitoring or upgrade all dependencies merely because a checklist
mentions them. Evaluate the changed dependency surface and the existing project
process. Commands below illustrate npm only.

#### Regular Updates
```bash
# Check for vulnerabilities
npm audit

# Check for outdated packages
npm outdated
```

Use the project's package manager. Review affected versions and compatibility, make targeted updates, then rerun checks; do not treat `npm audit fix` or a blanket update as a verified repair.

#### Lock Files
```bash
# Preserve the project's package-manager lockfile convention
git add package-lock.json

# Use in CI/CD for reproducible builds
npm ci  # Instead of npm install
```

#### Verification Steps
- [ ] Changed dependencies checked against relevant advisories and supported versions
- [ ] Findings assessed and addressed or explicitly reported; a clean audit is not proof of security
- [ ] Lock files committed
- [ ] The repository's dependency monitoring mechanism is configured
- [ ] Regular security updates

## Abuse limits

Review whether the changed operation needs a tighter request/body/concurrency or
cost limit. Verify trusted client identity, bounded shared enforcement state and
outage behavior using [backend operational contracts](../../backend-patterns/references/operational-contracts.md).
Do not assume an IP header is trustworthy or that process-local counters protect
multiple workers. Test boundary values, concurrent abuse and the chosen failure
policy where the risk warrants it; a fixed 101-request test is not universal proof.

## Completion evidence

For affected boundaries, record protected resource, attacker-controlled input,
control location, actual positive/negative checks and unresolved gaps. Follow the
repository's deployment requirements without adding unrelated scans, integrations
or permission prompts. Findings from a repository audit use `codex-security`.
