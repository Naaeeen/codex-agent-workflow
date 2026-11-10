---
name: x-api
description: X/Twitter API integration for posting tweets, threads, reading timelines, search, and analytics. Covers OAuth auth patterns, rate limits, and platform-native content posting. Use when the user wants to interact with X programmatically.
---

# X API

Programmatic interaction with X (Twitter) for posting, reading, searching, and analytics.

## When to Activate

- User wants to post tweets or threads programmatically
- Reading timeline, mentions, or user data from X
- Searching X for content, trends, or conversations
- Building X integrations or bots
- Analytics and engagement tracking
- User says "post to X", "tweet", "X API", or "Twitter API"

## Authentication

### OAuth 2.0 Bearer Token (App-Only)

Use for endpoints that currently permit app-only authentication and the account's access tier. An app-only bearer token cannot act as a user to create Posts; OAuth 2.0 user tokens are a different credential type.

```bash
# Environment setup
export X_BEARER_TOKEN="your-bearer-token"
```

```python
import os
import requests

bearer = os.environ["X_BEARER_TOKEN"]
headers = {"Authorization": f"Bearer {bearer}"}

# Search recent tweets
resp = requests.get(
    "https://api.x.com/2/tweets/search/recent",
    headers=headers,
    params={"query": "claude code", "max_results": 10},
    timeout=(10, 30),
)
resp.raise_for_status()
tweets = resp.json()
```

### OAuth 1.0a (User Context)

One supported user-context option for endpoints that allow it. OAuth 1.0a is not required for all writes: OAuth 2.0 Authorization Code with PKCE also supports creating Posts with the required user scopes. Check each endpoint's current authentication mapping.

```bash
# Environment setup — source before use
export X_CONSUMER_KEY="your-consumer-key"
export X_CONSUMER_SECRET="your-consumer-secret"
export X_ACCESS_TOKEN="your-access-token"
export X_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

Legacy aliases such as `X_API_KEY`, `X_API_SECRET`, and `X_ACCESS_SECRET` may exist in older setups. Prefer the `X_CONSUMER_*` and `X_ACCESS_TOKEN_SECRET` names when documenting or wiring new flows.

```python
import os
from requests_oauthlib import OAuth1Session

oauth = OAuth1Session(
    os.environ["X_CONSUMER_KEY"],
    client_secret=os.environ["X_CONSUMER_SECRET"],
    resource_owner_key=os.environ["X_ACCESS_TOKEN"],
    resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
)
```

### OAuth 2.0 User Context (Authorization Code with PKCE)

Use the project's existing OAuth implementation. Validate state and redirect URI,
use PKCE, and obtain only the endpoint's required scopes (creating Posts currently
uses `tweet.read`, `tweet.write`, and `users.read`; request `offline.access` only when
refresh access is needed). Keep user access/refresh tokens separate from app-only tokens.
See [X PKCE and scopes](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code)
and [authentication mapping](https://docs.x.com/fundamentals/authentication/guides/v2-authentication-mapping).

The code below uses `oauth` as an already-authorized requests-compatible Session
(OAuth1Session, or a Session with an OAuth 2.0 user Authorization header).
Posting, deletion, and account changes require scoped user authorization.

## Core Operations

### Post a Tweet

```python
resp = oauth.post(
    "https://api.x.com/2/tweets",
    json={"text": "Hello from Codex"},
    timeout=(10, 30),
)
resp.raise_for_status()
tweet_id = resp.json()["data"]["id"]
```

### Post a Thread

```python
class ThreadPostError(RuntimeError):
    def __init__(self, confirmed_ids, failed_index):
        super().__init__(f"Thread stopped at item {failed_index + 1}; reconcile before retrying")
        self.confirmed_ids = tuple(confirmed_ids)
        self.failed_index = failed_index


def post_thread(oauth, tweets: list[str]) -> list[str]:
    ids = []
    reply_to = None
    for text in tweets:
        payload = {"text": text}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        try:
            resp = oauth.post("https://api.x.com/2/tweets", json=payload, timeout=(10, 30))
            resp.raise_for_status()
            tweet_id = resp.json()["data"]["id"]
        except (requests.RequestException, KeyError, ValueError):
            raise ThreadPostError(ids, len(ids)) from None
        ids.append(tweet_id)
        reply_to = tweet_id
    return ids
```

A thread can partially publish. Catch `ThreadPostError`, persist its `confirmed_ids` in the task's authorized state, and report `failed_index`. Do not automatically retry an ambiguous timeout: the Post may already exist. Reconcile before resuming, and do not delete published items without authorization.

### Read User Timeline

```python
resp = requests.get(
    f"https://api.x.com/2/users/{user_id}/tweets",
    headers=headers,
    params={
        "max_results": 10,
        "tweet.fields": "created_at,public_metrics",
    },
    timeout=(10, 30),
)
resp.raise_for_status()
```

### Search Tweets

```python
resp = requests.get(
    "https://api.x.com/2/tweets/search/recent",
    headers=headers,
    params={
        "query": "from:affaanmustafa -is:retweet",
        "max_results": 10,
        "tweet.fields": "public_metrics,created_at",
    },
    timeout=(10, 30),
)
resp.raise_for_status()
```

### Pull Recent Original Posts for Voice Modeling

```python
resp = requests.get(
    "https://api.x.com/2/tweets/search/recent",
    headers=headers,
    params={
        "query": "from:affaanmustafa -is:retweet -is:reply",
        "max_results": 25,
        "tweet.fields": "created_at,public_metrics",
    },
    timeout=(10, 30),
)
resp.raise_for_status()
voice_samples = resp.json()
```

### Get User by Username

```python
resp = requests.get(
    "https://api.x.com/2/users/by/username/affaanmustafa",
    headers=headers,
    params={"user.fields": "public_metrics,description,created_at"},
    timeout=(10, 30),
)
resp.raise_for_status()
```

### Upload Media and Post

Use the current [X media upload API](https://docs.x.com/x-api/media/introduction)
and the upload mode required by the media type. Verify authentication/scopes,
limits, and any asynchronous processing status; a successful upload alone does
not prove it is ready to attach. Do not assume uploads always use the legacy v1.1
endpoint. After the upload is complete and the content is authorized for posting:

```python
resp = oauth.post(
    "https://api.x.com/2/tweets",
    json={"text": "Check this out", "media": {"media_ids": [media_id]}},
    timeout=(10, 30),
)
resp.raise_for_status()
tweet_id = resp.json()["data"]["id"]
```

## Rate Limits

X API rate limits vary by endpoint, auth method, and account tier, and they change over time. Always:
- Check the current X developer docs before hardcoding assumptions
- Read `x-rate-limit-remaining` and `x-rate-limit-reset` headers at runtime
- Back off automatically instead of relying on static tables in code

```python
import time

remaining = int(resp.headers.get("x-rate-limit-remaining", 0))
if remaining < 5:
    reset = int(resp.headers.get("x-rate-limit-reset", 0))
    wait = max(0, reset - int(time.time()))
    print(f"Rate limit approaching. Resets in {wait}s")
```

## Error Handling

```python
resp = oauth.post("https://api.x.com/2/tweets", json={"text": content}, timeout=(10, 30))
if resp.status_code == 201:
    return resp.json()["data"]["id"]
elif resp.status_code == 429:
    reset = int(resp.headers["x-rate-limit-reset"])
    raise Exception(f"Rate limited. Resets at {reset}")
elif resp.status_code == 403:
    raise Exception(f"Forbidden: {resp.json().get('detail', 'check permissions')}")
else:
    raise Exception(f"X API error {resp.status_code}: {resp.text}")
```

## Security

- **Never hardcode tokens.** Use environment variables or `.env` files.
- **Never commit `.env` files.** Add to `.gitignore`.
- **If tokens are exposed**, report the exposure and obtain scoped authorization for revocation/rotation; do not print the token.
- **Use read-only tokens** when write access is not needed.
- **Store OAuth secrets securely** — not in source code or logs.

## Content handoff

An API integration or an explicitly supplied finished post does not require
voice profiling or content generation. For a writing request, reuse the already
approved draft/profile from the authoring workflow. Verify current platform
constraints and the exact target account/content before a write. Existing scoped
authorization counts; never repeat a content-generation loop as a posting prerequisite.

## Related Skills

- `brand-voice` — Build a reusable voice profile from real X and site/source material
- `content-engine` — Generate platform-native content for X
- `crosspost` — Distribute content across X, LinkedIn, and other platforms
- Use another workflow only if it is installed and required by the authorized task; do not change the user's social graph as preparation for drafting.
