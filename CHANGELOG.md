# Changelog

## 1.2.0 — Unreleased

Proposed protocol update; not yet released or runtime-verified.

- Add bounded execution and recovery guidance, with an optional UltraTerm mapping.
- Document the 10-minute default and 8-hour absolute run ceiling, including queue time.
- Document explicit `maxTurns`: default 64, maximum 2048 per worker, with bounded native compaction and retry.
- Document disk checkpoints, diagnostic inspection, and explicit resume of unfinished tasks only; no automatic replay or daemon survival.
- Require completion delivery at the parent idle boundary rather than behind the next user message.
- Preserve protocol major version 1 compatibility and telemetry version 1 through additive fields; no dependencies or provider routing changes.
- Extend offline public-contract tests; these are not host-runtime or production verification.
