# UltraTerm Subagent Protocol (USAP)

[Latest release](https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest) · [MIT License](LICENSE) · Agent skill · Vendor neutral

A vendor-neutral skill for agent runtimes with subagents. It gives the primary agent a delegation contract, file ownership rules, and an integration checklist. Load it before dividing a task so each worker gets a bounded assignment and every result gets reviewed.

The skill is text, not runtime enforcement. It needs no credentials or network access after installation.

## Protocol

1. **Routing pass** — decide whether delegation shortens the time to a correct result before dispatching anything. Simple, coupled, or judgment-heavy work stays with the primary.
2. **Adaptive concurrency** — one agent per genuinely independent leaf, from zero to as many as the host can carry; parallelize DAG siblings and, where the host supports intra-batch dependencies, use bounded handoffs (`author -> verifier`) instead of unnecessary parent round-trips.
3. **Capability routing** — send each leaf to the cheapest model tier that can finish it reliably; escalate on ambiguity, blast radius, or failed attempts, and on host-managed implicit chains allow bounded in-place failover for transient provider errors while keeping explicit routes fail-closed and reporting policy refusals.
4. **Dispatch contract** — brief every leaf with target, change, acceptance, ownership, and scope limits; pass context through files or—when supported by the host and recipient—indexed `#seq` board citations, and where supported isolate multi-writer git batches in per-task worktrees (host never auto-pushes) or warm-fork persisted transcripts without duplicating scratch, build, or worktree directories.
5. **Integration gate** — the primary inspects every report and changed surface, reviews and merges any isolated worktree branch receipts, runs focused checks, relies on deterministic host stall diagnostics rather than extra LLM monitor/narrator agents, and validates once after integration. A subagent's "done" is evidence to inspect, not completion proof.

The primary agent always owns interpretation, decomposition, cross-task contracts, consequential judgment, integration, verification, and the final answer. Subagents are bounded execution capacity, never replacement orchestrators.

## Install

The installer downloads a release, verifies its archive checksum, and prints the installed version. On macOS and Linux it requires `curl` (or `wget`), `tar`, and `sha256sum` or `shasum`, plus standard shell utilities. Windows uses built-in PowerShell commands.

macOS and Linux:

```sh
curl -fsSL https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest/download/install.sh | sh
```

Windows, in Windows PowerShell 5.1 or PowerShell 7:

```powershell
irm https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest/download/install.ps1 | iex
```

The skill goes to `~/.config/agents/skills/ultraterm-subagent-protocol` (on Windows, `%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol`). The installer needs no runtime, Node, Python, or sudo, and it does not edit your shell profile or PATH. To update, run the same line again; it upgrades in place. To pin a version, put `USAP_VERSION=1.7.1` before `sh` (macOS and Linux) or set `$env:USAP_VERSION` first (Windows). To remove USAP, delete that folder. A git clone in that folder is never replaced: a clean one is updated in place with `git pull --ff-only`, and one with local changes or that cannot fast-forward is left untouched with a message. A symbolic link there is also left alone. Existing copies containing nested links or `.git` entries are refused. Pinned installs refuse git checkouts; use `git fetch --tags` and `git checkout v1.7.1` yourself instead.

Installer variables: `USAP_SKILLS_DIR` selects the skills folder (default `~/.config/agents/skills`); it does not move an existing installation. Installer assets start at v1.5.0; use the manual clone route for older releases.

Manual route: clone a release into a skill directory recognized by your agent runtime:

```sh
git clone --branch v1.7.1 https://github.com/michael-berardi/ultraterm-subagent-protocol.git \
  ~/.config/agents/skills/ultraterm-subagent-protocol
```

The installed path must contain `SKILL.md`. For project-local installation, copy the repository to your runtime's project skill directory, commonly `.agents/skills/ultraterm-subagent-protocol` or `.claude/skills/ultraterm-subagent-protocol`.

UltraTerm maintains its bundled, host-specific variant as a managed resource. Its version and routing policies are independent of this portable release; do not overwrite managed helpers or assume identical capabilities.

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
  has no shell permission, and skips project-wide builds and suites.
  Budget: 10 minutes per batch, 64 turns per leaf, including retries.
  Parent owns integrated validation; leaves report evidence and risks.
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

USAP is a skill contract, not a service. The source checkout contains (release archives omit `tests/` and `scripts/`):

- [`SKILL.md`](SKILL.md) — the protocol: routing pass, adaptive batch width, capability routing table, dispatch contract, coordination and isolation rules (host-supported bounded DAG handoffs, `#seq` board references with fallback, multi-writer git worktrees), bounded execution and recovery (bounded implicit in-place failover, warm transcript forking, deterministic stall diagnostics), integration gate, and efficiency scorecard.
- [`references/omp.md`](references/omp.md) — an optional mapping of the protocol onto OMP's `task` and `hub` tools.
- [`references/ultraterm.md`](references/ultraterm.md) — optional host-specific budgets, `dependsOn` intra-run handoffs, non-destructive `#seq` / `seqs` board reads, automatic `workspace` git worktrees, warm `forkFrom` transcripts, bounded implicit mid-run failover, explicit resume replacement routes, idle-stream watchdogs, permissions, checkpoints, explicit resume, deterministic stall diagnostics, and completion delivery.
- `tests/test_skill.py` — deterministic checks of the public contract: portable frontmatter, core invariants, context-efficiency and disclosure limits, required files, cross-file rule consistency, and README freshness.
- `scripts/install.sh` and `scripts/install.ps1` — the one-line installers. They download and verify archives, replace plain skill copies, or fast-forward existing git checkouts; they do not run the skill.

USAP guarantees a deterministic *process*: the routing pass, capacity rule, dispatch contract shape, and integration gate in `SKILL.md` are testable, reviewable text.

This describes the written process, not a guarantee that a host or model follows it. The skill is text, not executable enforcement. The repository has no telemetry. Optional mappings describe host behavior, not capabilities supplied by installing the skill. Check the running host's schema and diagnostics before using them; source inspection is not end-to-end recovery proof.

## Privacy

The installed skill makes no network calls and sends no telemetry, analytics, crash reports, or usage data. It is plain text: it stores no logs, history, transcripts, or credentials and creates no files beyond its installed folder. To remove it, delete `~/.config/agents/skills/ultraterm-subagent-protocol` (`%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol` on Windows).

Network access happens only when you ask for it:

- Running the install or update command downloads the installer, release archive, and `SHA256SUMS` from GitHub; the archive is checked before installation. A clean git checkout is fast-forwarded from the remote you configured there. Nothing is uploaded.
- Using the skill with an agent sends your task briefs, prompts, and worker output to the model provider your agent is configured to use. That provider's retention applies; USAP adds no account or service.
- Clicking a documentation link opens GitHub or the project page.

These docs load no remote images, fonts, scripts, or other third-party assets.

## Security and safety

The installed skill needs no credentials, network access, or executable dependencies. The installers require network access for public releases and refuse archives whose SHA-256 does not match `SHA256SUMS`. Checksums detect corruption, not a compromised release publisher. The one-line commands execute the downloaded installer without independently verifying it; download and inspect it first if required by your trust policy. Its safety posture lives in the protocol itself: one writer per shared file (with host-supported per-task git worktrees isolating multi-writer batches without host auto-push, while remaining a workflow boundary rather than an OS sandbox), weak or free models never own consequential decisions unverified, and retrieved content plus subagent output are treated as untrusted evidence until the primary verifies them. See [SECURITY.md](SECURITY.md) for the reporting policy.

## Validate

```sh
python3 -m unittest discover -s tests -v
```

The suite uses only the Python standard library. It checks documentation contracts, not runtime enforcement or host recovery.

From a clean committed checkout, build the release and run the shell installer tests (offline, using a local release copy):

```sh
scripts/build-release.sh && scripts/test-install.sh
```

The build writes `dist/release/` and packages `HEAD`, not uncommitted edits. PowerShell tests are separate: see the setup and invocation in `scripts/test-install.ps1`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Versioning and releases

The canonical version is `metadata.version` in [`SKILL.md`](SKILL.md) (currently 1.7.1), following semantic versioning: breaking contract changes bump the major version, new protocol sections the minor version, and wording fixes the patch version. Each release is tagged `vX.Y.Z` with notes on the [releases page](https://github.com/michael-berardi/ultraterm-subagent-protocol/releases) and in [CHANGELOG.md](CHANGELOG.md); behavioral changes ship with their README and test updates in the same commit.

## License

MIT. See [LICENSE](LICENSE).

---

Part of [Pareto Cybernetics](https://paretocybernetics.com/projects/usap/): free, private, open-source tools for working with AI agents.
