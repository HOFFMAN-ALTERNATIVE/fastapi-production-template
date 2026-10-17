# 0001. Stateless JWT access and refresh tokens

Status: accepted
Date: 2026-10-17

## Context
The template is a starting point for API services called by SPAs, mobile apps and
scripts. Most requests are authenticated, so the auth check sits on the hot path.
Postgres and Redis are already in the stack, but adding a lookup to every request
is a cost every service built from it would inherit.

## Options
1. Server-side sessions in Redis: easy revocation, but a Redis read per request and a
   cookie flow that does not suit non-browser clients well.
2. Opaque bearer tokens in Postgres: revocable, but a DB read per request.
3. JWTs signed with HS256: a short-lived access token (15 min) and a refresh token
   (7 days), each with `type` and `jti` claims, checked without any lookup.

## Decision
Option 3. Verification is local and cheap, and the short access TTL limits the damage
of a stolen access token.

## Consequences
- `decode_token` requires `exp`, `sub` and `type`, and rejects a refresh token used as
  an access token and the other way round.
- Staging and production refuse to start with the placeholder secret or one shorter
  than 32 characters.
- Refresh tokens are not stored, so they cannot be revoked one by one before expiry.
  The `jti` claim is there so a deny-list can be added without changing the token format.
- One shared HS256 secret means any service that verifies tokens can also mint them.
  Move to an asymmetric algorithm when a second service needs to verify.
