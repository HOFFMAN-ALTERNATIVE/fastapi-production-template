# 0002. Run Alembic on container start, check the round trip in CI

Status: accepted
Date: 2026-10-17

## Context
Schema changes ship with code. A template should make the safe path the default: the
schema matches the code when the app starts, and every migration can be rolled back.
Most services built from it start as one container.

## Options
1. Manual `alembic upgrade head` before each deploy: flexible, and easy to forget.
2. A separate migration job in the orchestrator: correct for many replicas, but
   needs Kubernetes Jobs or similar, which a template cannot assume.
3. `alembic upgrade head && exec uvicorn ...` as the container command, plus a CI job
   that runs `upgrade`, `downgrade base`, `upgrade` again and `alembic check` against a
   real Postgres.

## Decision
Option 3. For one container it removes a manual step, and the CI round trip catches
broken downgrades and model drift before merge.

## Consequences
- A failed migration stops the container from starting, so a half-migrated app never
  serves traffic.
- `alembic check` fails CI when models change without a migration.
- With several replicas starting at the same time, they race to migrate. The README
  says to run the upgrade as a one-off job in that case.
- Downgrades are tested on an empty database only, not with production data.
