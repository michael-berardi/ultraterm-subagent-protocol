# OMP integration

Apply USAP with OMP's native `task` tool and `hub` coordination.

## One-wave dispatch

Put independent leaves in one `task` call, up to the USAP concurrency ceiling; queue the rest for the next wave. Shared batch context defines the goal, constraints, and cross-task contract. Each task defines its target, change or investigation, non-goals, ownership, and acceptance output.

Use the most specific installed agent:

- `scout` or a cheaper scout for read-only evidence;
- `task` or a cheaper implementation agent for bounded edits;
- `reviewer`, `security-reviewer`, or `designer` for specialist judgment;
- optional provider specialists only when they materially improve that leaf.

Never pass routine work to a quality specialist merely because capacity exists. Never put weak or free agents on an unverified consequential path.

## Coordination

- Use `hub send` for a concrete interface or ownership conflict, not status polling.
- Let results auto-deliver while the primary reads, integrates, or prepares verification.
- If blocked with no local work, use one bounded wait rather than repeated short polls.
- One writer owns each file; a sibling that needs a change in another's file sends it to that owner.
- Parent verification covers the integrated result. Every child skips formatters, linters, builds, and project-wide tests unless its isolated acceptance contract explicitly requires a focused check.

## Suggested OMP batch contract

```text
# Goal
What the batch accomplishes.

# Constraints
Safety rules, model/risk boundaries, validation ownership, and non-goals.

# Contract
Interfaces and artifacts shared between leaves.
```

```text
# Target
Exact files, symbols, subsystem, or evidence question; exclusive ownership.

# Change
Operations or research to perform; explicit scope boundary.

# Acceptance
Observable result and concise return contract; no project-wide validation.
```

The primary reviews every returned claim and change before using it.