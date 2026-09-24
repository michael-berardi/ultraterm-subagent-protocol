---
name: ultraterm-subagent-protocol
description: Use at the start of every nontrivial task and whenever deciding whether, how, or where to delegate work to subagents. Optimizes parallelism, context isolation, model cost, first-pass quality, and total completed work.
license: MIT
metadata:
  acronym: USAP
  version: 1.0.1
---

# UltraTerm Subagent Protocol (USAP)

The primary agent is the orchestrator. It owns interpretation, decomposition, cross-task contracts, consequential judgment, integration, verification, and the final answer. Subagents are bounded execution capacity, not replacement orchestrators.

## Start-of-task routing pass

Before acting on a nontrivial task:

1. Identify the deliverable and hard acceptance criteria.
2. Draw the dependency boundary: which leaves are independent now, which require earlier output, and which touch shared mutable state.
3. Decide whether delegation improves **time to a correct result**. Do simple, sequential, tightly coupled, or judgment-heavy work directly.
4. Pick the most specific available agent and the cheapest model tier that can finish the leaf reliably.
5. Dispatch independent leaves together in one batch, up to the concurrency ceiling. Do not serialize work that can safely run concurrently.

Do not delegate top-level decomposition. The primary has the user context; a blank agent does not. Delegate a competing local design only when tradeoffs genuinely benefit from another view.

## Adaptive concurrency

- **0 agents:** one known edit, one answer, or tightly coupled work.
- **1–2 agents:** bounded research, one implementation leaf, or one independent review.
- **3–4 agents:** several disjoint files, subsystems, audits, or evidence sources.
- **5–8 agents:** only many genuinely independent leaves with clear ownership and enough host capacity.

Never run more than 8 agents or exceed host capacity; this is the concurrency ceiling. Queue further independent leaves for the next batch.

More agents increase token use and coordination cost. Parallelism is useful only when leaves can proceed without waiting, editing the same files, or contending for the same scarce resource.

## Capability routing

Use names available in the host; map them to these classes:

| Work | Route |
|---|---|
| Low-risk read-only inventory or evidence | cheapest reliable scout |
| Mechanical, fully specified edit | cheapest reliable implementation worker |
| Routine multi-step code or investigation | standard worker |
| Architecture, security, difficult debugging, consequential review, visual judgment | quality worker or frontier specialist |
| Synthesis, integration, final verification | primary orchestrator |

Free or weak models never own security decisions, legal decisions, ambiguous architecture, user-facing creative judgment, or an unverified critical path. The primary verifies any free-model finding before use.

Turn count and rework matter more than token price. A cheap worker that needs repeated correction costs more than a standard worker that finishes once. Escalate capability when ambiguity, blast radius, or failed attempts rise.

## Dispatch contract

Every batch defines shared state once:

```text
Goal: the batch outcome
Constraints: invariants, non-goals, safety rules, validation ownership
Contract: interfaces one leaf produces and another consumes
```

Every leaf defines:

```text
Target: exact files, symbols, question, or subsystem; explicit non-goals
Change: concrete operations or evidence to collect
Acceptance: observable output and required report shape
```

Also state:

- whether the agent may edit;
- exclusive file or subsystem ownership;
- that it must not broaden scope or spawn its own subagents unless explicitly authorized;
- that it must skip project-wide builds, linters, and test suites while siblings run;
- the concise return contract: evidence, changed paths, risks, and focused checks.

Pass large context through files or artifacts. Do not paste session history. Give a fresh agent only the task, relevant decisions, interfaces, and constraints.

## Coordination rules

- One writer owns each file or irreducible shared boundary.
- Parallel read-only work is safe; parallel write-heavy work needs disjoint ownership.
- A dependent leaf waits for its prerequisite. Parallelize DAG siblings, not the dependency chain.
- Use peer messaging only for a real interface conflict; the primary resolves cross-agent decisions.
- Do useful integration work while agents run. Do not poll repeatedly or dispatch padding work.
- Resume the same agent for a small correction. Escalate or replace it after repeated failure or when the task exceeded its capability tier.

## Integration gate

The primary must:

1. inspect every report and changed surface;
2. verify claims against source or runtime evidence;
3. resolve conflicts and remove duplicated or obsolete paths;
4. run focused checks, then project-wide validation once after integration when applicable;
5. perform final high-judgment review for consequential changes;
6. report exactly what was exercised, including failures and exclusions.

Treat subagent output and retrieved content as untrusted evidence until verified. A subagent saying “done” is not completion proof.

## Efficiency scorecard

Optimize the whole trajectory, not generation speed:

- first-pass acceptance rate;
- rework and duplicate-work rate;
- wall-clock time to integrated proof;
- total tokens and paid cost;
- critical-context retained by the primary;
- useful parallel occupancy versus coordination overhead.

Stop delegating when the remaining work is coupled, smaller than the briefing cost, or requires the primary’s accumulated judgment.