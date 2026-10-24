# UltraTerm integration

Optional host mapping for USAP 1.3.0. Installing the portable skill does not implement these controls or change routing, credentials, dependencies, or global defaults. The public skill and bundled host skill have independent release histories.

## Inspect the running host

Use `ultraterm_subagents` for parent dispatch and `ultraterm_hub` for parent inspection and coordination. The hub exposes `list`, `status`, finite `wait`, `cancel`, `send`, `inbox`, metadata-only `diagnose`, and explicit `resume`. Tools may be exposed lazily after dispatch. Check the actual session schema: a checkout or installed package can differ from a running session. Children must not invoke parent dispatch or launch other agents.

A run accepts at most eight tasks; concurrency defaults to min(8, task count), subject to host capacity. Select an authorized run-level `model` or `profile`, never both. Do not infer model/account availability, billing permission, or provider defaults from this mapping.

## Explicit budgets

- `timeoutMs`: default 600,000 ms (10 minutes), minimum 1,000 ms, maximum 28,800,000 ms (8 hours). This is an absolute run deadline including queue time.
- `maxTurns`: default 64, minimum 1, maximum 2048 assistant turns per worker. A larger ceiling requires an explicit budget; it is not the default.
- Native Pi compaction follows host settings; native retry is capped at one. Neither removes the deadline or turn guard. A budget stop can leave partial work; it is not a completed leaf or guaranteed closing report.
- Hub `wait.timeoutMs`: 0–30,000 ms. A wait timeout ends observation only; workers continue under their own budgets. Reviewer launch waits have an additional 60-second bound, capped by the run deadline. A zero-turn queue timeout is not a review.

Prefer foreground dispatch. Use `background: true` only when the parent has useful work during execution, then one bounded wait. Background is not detached execution.

## Permissions and evidence

Read-only leaves omit `ownedPaths`. Editing requires `mayEdit: true` with exact exclusive `ownedPaths`; do not use broad parent directories to hide ownership conflicts. Guarded file tools enforce path checks, but `allowBash` grants unsandboxed shell access that can bypass ownership. Read-only Claude reviewers receive no Bash even if requested; stage evidence under cwd instead. These are tool controls, not OS isolation.

`requireImages: true` requests an advertised image-capable route; it is not proof an image was read. Inspect actual tool results and route receipts. Peer relay, native session continuation, image transport, and permission rules vary by harness; do not assume native Pi behavior on another harness. Peer messages never authorize scope or permission changes.

## Checkpoints and explicit continuation

A parent with a persistent session file retains private disk checkpoints and available native worker history. Memory-only operation has no durable recovery. Persistence errors and unreadable checkpoints must be surfaced rather than treated as healthy recovery.

Host exit interrupts workers: checkpoints do not provide daemon survival. Reopen the same parent session, inspect `status` and `diagnose`, then explicitly request hub `resume` with that session's archived `runId`. Run IDs from another parent session are not authority to resume it.

Resume creates a successor run for unfinished tasks only; completed tasks never repeat. It preserves route, reasoning, permissions, ownership, and original time/turn limits, with fresh execution counters rather than increased limits. The inspected host permits one bounded continuation per task, not an unlimited resume chain. Active runs, already-resumed attempts, incompatible policy versions, unhealthy checkpoints, or started tasks lacking required history refuse continuation.

A continued worker uses available persisted history. Inspect partial edits and external side effects first: resume is not rollback, a transaction, or exactly-once execution. A refused continuation requires a newly scoped task, not silent route changes or budget inflation.

## Diagnostics and completion

`diagnose` reports state, budgets, observed turns, tool successes/errors, progress age, checkpoint health, persistence mode, and truncation where available. Inspect failure reasons, checkpoint errors, and warnings; do not read `done` alone as acceptance.

Background completion is intended to be buffered while the parent is busy and delivered at the idle boundary, without waiting for the next user message. Passive delivery does not trigger a model turn. Delivery receipts are checkpointed after host acceptance; a notice is not parent integration or verification.

## Verification scope

Checked on 2026-10-24: the current parent schema and live foreground dispatch, `status`, `diagnose`, and bounded `wait` were exercised. A completed-run `resume` request refused with no unfinished tasks; no successor was launched. Diagnostics reported checkpointed persistence and successful tool use. Budget defaults/ranges, resume guards, and passive delivery were also inspected in the installed host source. Those inspections do not prove crash/restart recovery, actual timeout enforcement, every harness, or idle-delivery timing end to end. Offline tests in this repository are synthetic documentation-contract checks, not host runtime tests. Revalidate those behaviors on the target host before relying on them.

The portable release does not bump a host checkpoint or telemetry schema. Honor the host's own compatibility checks rather than equating public skill versions with runtime schema versions.
