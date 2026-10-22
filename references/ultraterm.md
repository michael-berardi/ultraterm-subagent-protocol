# UltraTerm integration — proposed USAP 1.2.0 (Unreleased)

This optional mapping describes the inspected host implementation, not a verified release. The portable skill does not implement these controls. No dependencies or provider routing changes are required.

## Explicit budgets

- `ultraterm_subagents.timeoutMs`: default 600,000 ms (10 minutes), minimum 1,000 ms, maximum 28,800,000 ms (8 hours). This is an absolute run deadline including queue time, not a per-tool timeout.
- `ultraterm_subagents.maxTurns`: default 64, minimum 1, maximum 2048 per worker. Explicitly request a larger budget for long-horizon work; the ceiling is not the default.
- The worker turn guard counts assistant turns and reserves three of the budget for the closing report. At the warning threshold it steers a still-tool-using worker to stop gathering new evidence; the next over-limit turn start aborts the session. There is no separately driven final-report turn, so a worker that ignores the steer can settle with whatever it has already produced.
- Native compaction is enabled under the host's compaction settings; native retry is enabled with `maxRetries: 1`. Neither grants unbounded execution or resets the run deadline. Compaction/retry phases appear in progress reporting.
- `ultraterm_hub` action `wait` has a finite observation window. Its timeout ends observation only; workers continue until their own deadline, completion, or cancellation.

## Checkpoints and explicit continuation

Disk checkpoints persist run/task records and native worker session history when the parent has a persistent session file. Without one, operation is memory-only; do not assume recovery is available. Persistence errors and unreadable checkpoints must be surfaced, not silently treated as durable recovery.

Host exit interrupts workers: checkpoints do not provide daemon survival. Reopening a session restores inspection state, not automatic replay or execution. Inspect `status` and `diagnose`, then explicitly request `ultraterm_hub` action `resume` with the archived `runId` if continuation is appropriate.

Resume creates a successor run for unfinished tasks only (tasks not marked `done`), preserving the original model, reasoning level, ownership, and budget settings; the successor run receives a fresh budget rather than continuing the predecessor's exhausted counters. Completed tasks never repeat. Healthy durable checkpoints are required; a previously started task without native history cannot resume. Active runs and already-resumed predecessors are rejected to avoid duplicate work.

A resumed worker continues persisted history without replaying its original prompt. It must inspect current owned files before acting and treat past tool results as historical evidence. Resume is not a rollback, transaction, or guarantee of exactly-once side effects; review partial edits and commands first.

## Diagnose and completion delivery

`ultraterm_hub` action `diagnose` with `runId` reports run/task state, time and turn budgets, turns, tool successes/errors, progress age, checkpoint availability, and output truncation. Reasons distinguish host interruption, deadline, turn budget, cancellation, provider/authentication failures, and tool/worker failures where observable. Persistence mode, checkpoint errors, and warnings are included. Diagnosis is evidence for the parent, not an automatic retry instruction.

Background completions are buffered while the parent is busy and delivered at the actual idle boundary, not dumped behind the next user message. Passive delivery does not trigger a model turn; delivery receipts are checkpointed after acceptance. Notices still require parent integration and verification.

## Compatibility

USAP 1.2 retains protocol major version 1 compatibility. Host telemetry remains numeric version 1 with additive fields; readers should tolerate unfamiliar optional fields. This document does not change provider selection, dependency policy, or credentials. The proposal requires separate host validation before release.
