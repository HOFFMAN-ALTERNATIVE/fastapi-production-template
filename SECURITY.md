# Security

## Reporting

Use GitHub's private "Report a vulnerability" button on this repository. I aim to reply within 72 hours.

## Threat model

- **Assets:** user accounts and password hashes, JWT signing secret, per-user data.
- **Actors:** credential stuffers, authenticated users trying to read other users' data, anyone who learns the JWT secret.
- **Entry points:** `/api/v1/auth/*`, resource routes, `/metrics` and `/docs` if exposed.
- **Mitigations:** Argon2id hashing; login responses that do not reveal whether an account exists; Redis-backed login rate limit with `Retry-After`; typed access and refresh tokens with `jti`; per-owner isolation that returns 404 for other users' items; staging and production refuse placeholder or short JWT secrets; `/docs` disabled in production; non-root container; ruff bandit rules and `pip-audit` in CI.

## Not provided

- Token revocation or a refresh-token deny-list.
- Authentication on `/metrics`. Keep it on an internal network or behind the proxy.
- Multi-factor authentication.
