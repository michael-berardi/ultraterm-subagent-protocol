# UltraTerm Subagent Protocol (USAP)

A compact, vendor-neutral skill that tells a primary agent when and how to delegate work to subagents — so parallelism helps instead of inflating cost, context, and rework.

## The problem

Ad-hoc delegation fails in predictable ways: every task gets fanned out regardless of coupling, each subagent gets the strongest model regardless of difficulty, workers receive pasted session history instead of a contract, and the primary agent accepts "done" reports without verification. The result is more tokens, more coordination, and slower delivery of a correct result.

USAP replaces that with one explicit protocol, defined in [`SKILL.md`](SKILL.md):

1. **Routing pass** — decide whether delegation shortens the time to a correct result before dispatching anything. Simple, coupled, or judgment-heavy work stays with the primary.
2. **Adaptive concurrency** — scale agent count to genuinely independent leaves, from zero up to a bounded ceiling; never parallelize a dependency chain.
3. **Capability routing** — send each leaf to the cheapest model tier that can finish it reliably; escalate on ambiguity, blast radius, or failed attempts.
4. **Dispatch contract** — brief every leaf with target, change, acceptance, ownership, and scope limits; pass context through files, not history dumps.
5. **Integration gate** — the primary inspects every report and changed surface, runs focused checks, and validates once after integration. A subagent's "done" is evidence to inspect, not completion proof.

The primary agent always owns interpretation, decomposition, cross-task contracts, consequential judgment, integration, verification, and the final answer. Subagents are bounded execution capacity, never replacement orchestrators.

## Who it is for

Operators of agent runtimes that support subagents, model tiers, or peer coordination, who want a single portable delegation policy instead of per-task improvisation. USAP is instructions only — no runtime, no dependencies, no network access.

## Guarantees and non-guarantees

USAP guarantees a deterministic *process*: the routing pass, concurrency ceiling, dispatch contract shape, and integration gate in `SKILL.md` are testable, reviewable text.

USAP does **not** guarantee outcome metrics. Wall-clock time, token cost, and first-pass acceptance depend on the host runtime, the models available, and the task. The protocol defines an efficiency scorecard (first-pass acceptance, rework rate, time to integrated proof, total cost) so outcomes can be measured honestly rather than assumed.

## Install

Copy this repository into a skill directory recognized by your agent runtime:

```sh
git clone https://github.com/michael-berardi/ultraterm-subagent-protocol.git \
  ~/.config/agents/skills/ultraterm-subagent-protocol
```

The installed path must contain `SKILL.md`. For project-local installation, copy the repository to your runtime's project skill directory, commonly `.agents/skills/ultraterm-subagent-protocol` or `.claude/skills/ultraterm-subagent-protocol`.

UltraTerm installs and maintains this skill automatically as a managed resource.

## Quick start

Load USAP at the start of a nontrivial task, before deciding whether to delegate:

```text
Use the UltraTerm Subagent Protocol for this task.
```

Then follow the routing pass in `SKILL.md`. A dispatch batch that conforms to the contract looks like:

```text
Goal: ship the billing retry fix behind the existing flag.
Constraints: no schema changes; no new dependencies; each leaf may
  edit only its Target file, must not broaden scope or spawn subagents,
  and skips project-wide builds and suites.
Contract: billing/retry.ts exports RetryPolicy
  { maxAttempts: number; baseDelayMs: number; jitter: boolean };
  Leaf A implements it, Leaf B consumes exactly that shape.

Leaf A — Target: billing/retry.ts only. Change: add RetryPolicy and a
  backoff helper. Acceptance: file compiles; report changed path and
  exported symbol names.
Leaf B — Target: billing/worker.ts only. Change: replace inline retry
  loop with RetryPolicy. Acceptance: compiles against the Contract
  shape; report behavior deltas.
```

Leaf B runs alongside Leaf A because the Contract pins the interface it consumes. The primary integrates both leaves, verifies the interface actually matches, runs the focused retry test, and runs the project suite once at the end.

## Architecture and behavior

USAP is a skill contract, not a service. The repository contains:

- [`SKILL.md`](SKILL.md) — the protocol: routing pass, adaptive concurrency tiers, capability routing table, dispatch contract, coordination rules, integration gate, and efficiency scorecard.
- [`references/omp.md`](references/omp.md) — an optional mapping of the protocol onto OMP's `task` and `hub` tools.
- [`tests/test_skill.py`](tests/test_skill.py) — deterministic checks of the public contract: portable frontmatter, core invariants, context-efficiency and disclosure limits, required files, cross-file rule consistency, and README freshness.

Because the skill is text, behavior is exactly what the files say. There are no hidden defaults, install scripts, or telemetry.

## Security and safety

USAP needs no credentials, network access, or executable dependencies. Its safety posture lives in the protocol itself: one writer per shared file, weak or free models never own consequential decisions unverified, and retrieved content plus subagent output are treated as untrusted evidence until the primary verifies them. See [SECURITY.md](SECURITY.md) for the reporting policy.

## Validate

```sh
python3 -m unittest discover -s tests -v
```

The suite is standard-library only and runs offline in milliseconds.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep changes vendor-neutral, compact, and grounded in observable workflow outcomes; structural contract changes need a deterministic test.

## Versioning and releases

The canonical version is `metadata.version` in [`SKILL.md`](SKILL.md) (currently 1.0.1), following semantic versioning: breaking contract changes bump the major version, new protocol sections the minor version, and wording fixes the patch version. Releases are commits on `main`; behavioral changes ship with their README and test updates in the same commit.

## License

MIT. See [LICENSE](LICENSE).
