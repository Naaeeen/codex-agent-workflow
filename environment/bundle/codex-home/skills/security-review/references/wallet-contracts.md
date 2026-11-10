# Wallet-signing and transaction checks

Adapted from the installed local skill; see [provenance](provenance.md).
Code blocks are illustrative fragments, not complete applications. They have not
been compiled or executed in this documentation refactor. Check the installed
library version and the surrounding application contracts before adapting them.

### 9. Blockchain Security (Solana, only when relevant)

Use the installed SDK's actual message and transaction types. Do not treat a Solana
transaction as a generic `{ from, to, amount }` object or assume `verify` is exported
by `@solana/web3.js`. The current [Solana signing example](https://solana.com/developers/cookbook/wallets/sign-message)
uses `verifySignature(publicKey, signatureBytes, messageBytes)` from `@solana/kit`;
legacy SDKs need their own documented verification path. This is a contract checklist,
not runnable SDK code or a reason to migrate an existing project automatically.

- Decode the address and signature using their specified encodings; verify the exact
  signed bytes with the selected SDK.
- For login, bind the challenge to the origin/domain, intended account, session,
  one-time nonce, and expiry; consume it once to prevent replay.
- For transactions, decode every instruction and loaded account, verify program IDs,
  recipients, amount/base units, token mint, authority and requested privileges against
  the intended action. Check fees and recent blockhash/durable-nonce rules as applicable.
- Simulate where supported and validate the confirmed on-chain outcome. A preflight
  balance check or valid signature alone does not prove the operation safe or final.
- Never sign an unexplained transaction or send it without scoped authorization.
