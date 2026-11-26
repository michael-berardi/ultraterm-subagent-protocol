# Changelog

All notable changes to the UltraTerm Subagent Protocol are documented here.
The canonical version is `metadata.version` in [`SKILL.md`](SKILL.md) and
follows [Semantic Versioning](https://semver.org/).

## [1.7.1] - 2026-11-26

- Add a README `## Privacy` section: the installed skill makes no network calls or telemetry, the installer's downloads are user-invoked and checksum-verified, local files are only the installed text, and the agent's configured model provider sees the prompts sent to it.
- Remove third-party badge images from the README so opening the docs loads no external assets.
- Add an offline test that fails on telemetry/analytics SDKs or endpoints, embedded third-party assets, or network calls in the portable skill instructions.

## [1.7.0] - 2026-11-25

All 1.7.0 capabilities below are documented as portable protocol guidance and optional target-host contracts in the UltraTerm mapping; installing the portable skill does not implement host runtime controls, and these 1.7.0 target contracts were not part of the 2026-10-24 host inspection.

- Add host-supported bounded intra-batch DAG handoffs (`dependsOn` in the UltraTerm mapping) so acyclic `author -> verifier` pipelines run inside one dispatch with auto-forwarded predecessor pointers, a run budget covering the full chain, clean abort on failed dependencies, no unbounded peer ping-pong loops, and primary ownership of final judgment.
- Add host-supported zero-copy `#seq` / `seqs` board citations: cite indexed run-log entries when the recipient harness can read the board (falling back to a file path or short summary otherwise), mapped to non-destructive `ultraterm_relay` (`operation: "read"`) and `ultraterm_hub` (`inbox` `seqs`) reads.
- Add host-supported automatic isolated git worktrees for multi-writer batches (`workspace: "auto" | "worktree" | "shared"` in the UltraTerm mapping): runs declaring two or more `mayEdit: true` tasks in a git repository isolate automatically outside the repository tree from the run's base `HEAD` while single-writer and read-only leaves stay shared; disjoint `ownedPaths` still apply, read-only dependents inspect isolated predecessors only when the host grants `worktreePath` read-only or stages a diff summary under `cwd` (`baseCommit..branch` requires shell access), dirty or partial worktrees are retained for inspection/resume while startup orphan cleanup follows the same clean-only rule for unreferenced worktrees, the primary reviews and merges returned branch receipts in the integration gate, and the host never auto-pushes (noting `allowBash` remains unsandboxed).
- Add host-supported warm context-preserving transcript forking (`forkFrom` copying only the persisted session transcript within the same parent session, never scratch, build, or worktree directories), bounded automatic mid-run in-place failover on implicit chains for transient provider failures (keeping original time/turn budgets and leaf capability tiers, reporting policy/content-filter refusals as failures rather than routing around them, and keeping explicit routes strictly fail-closed), optional explicit replacement routes on hub `resume` for quota/upstream-stalled checkpoints (preserving capability tier and `requireImages` requirements), idle-stream watchdogs paused during active tool calls, and deterministic runtime stall diagnostics (`stalledTasks`, `unansweredRequests`, `awaitingDependencies`) with zero extra LLM narrator or monitor agents.
- Expand documentation contract and neutrality tests to cover all 1.7.0 protocol invariants, host-support qualifiers, verification-scope caveats, and UltraTerm mappings.

## [1.6.0] - 2026-11-15

- Batch width is adaptive. The fixed ceiling of 8 agents is gone: a batch is as wide as the work has independent leaves, bounded by host capacity (the host's own limits, provider rate limits, and the machine). The skill now says to let the host queue what it cannot start, and to send fewer at a time when a provider starts refusing requests.
- The UltraTerm mapping no longer states an eight-task run limit; it describes capacity-based scheduling.
- README: the pinned install example named a version without installer assets; links that broke inside release archives are fixed; checksum and trust requirements are stated.

## [1.5.2] - 2026-11-11

- Fix: both installers only checked the top level of an existing skill folder before replacing it. A folder that held a symbolic link, a junction or a nested `.git` was still moved aside and deleted recursively, and on Windows PowerShell 5.1 a recursive delete can follow a junction and delete what it points at. The installers now refuse, with one clear message and nothing changed, if the old copy contains any link or any `.git` at any depth, and the Windows installer removes the old copy with `[IO.Directory]::Delete`, which does not follow junctions.
- Fix: with `USAP_VERSION` set, a git checkout is no longer pulled to its branch head; the installer prints the `git fetch --tags` and `git checkout v<version>` commands and stops.
- Fix (Windows): `GIT_TERMINAL_PROMPT` is restored after the installer runs, so it no longer stays set in your session.
- Test all of the above, including a nested symlink, a nested `.git`, and a pinned install over a git checkout.

## [1.5.1] - 2026-11-11

- Fix data loss in both installers: when the skill folder was a git clone, the installer replaced it with a plain copy and deleted its `.git` folder, even when the clone was clean, taking local commits, stashes, branches and ignored files with it. A git clone is now never replaced: a clean one is updated in place with `git pull --ff-only`, and one with local changes or that cannot fast-forward is left untouched with a clear message.
- Refuse to replace a symbolic link or junction at the skill folder; on Windows removing one could delete the folder it pointed at. The message names the link target.
- Windows: unpack the download into a staging folder inside the skills folder, which avoids a failing move across drives on Windows PowerShell 5.1, and resolve a relative `USAP_SKILLS_DIR` the PowerShell way.
- Test the above, including a clean clone with an unpushed commit, a clone with a stash, a diverged clone and a symlinked folder.

## [1.5.0] - 2026-11-11

- Add one-line installers: `scripts/install.sh` for macOS and Linux and `scripts/install.ps1` for Windows. Each downloads the release, checks its SHA-256 before installing, and puts the skill in `~/.config/agents/skills/ultraterm-subagent-protocol`. Running it again upgrades in place. A git checkout with local changes is never overwritten.

## [1.4.1] - 2026-11-07

- Restore the real repository URL in the install command, release badge and changelog links; 1.4.0 replaced it with a `your-org` placeholder that returns 404.
- Test that every shipped GitHub URL names the published repository.

## [1.4.0] - 2026-11-01

Neutrality cleanup for public distribution.

- Replace personal repository owner names in shipped docs with neutral placeholders.
- Add a neutrality test that fails if a model id or personal name returns to shipped docs.

## [1.3.0] - 2026-10-24

Reconciles the unpublished 1.2.0 recovery draft with the portable safeguards from the bundled 1.3.0 skill. Version 1.2.0 was never a public release; bundled and public versions have independent histories.

- Add finite execution budgets, bounded peer requests, foreground/background guidance, checkpoint inspection, and explicit continuation of unfinished work.
- Clarify that completion notices arrive at the idle boundary and do not replace parent integration.
- Require explicit edit/shell permissions, omit write ownership for read-only leaves, and prohibit child launchers.
- Explain ownership versus sandboxing, shell bypass, message trust, secret handling, and honest partial/failure reporting.
- Add an optional UltraTerm mapping with budget ranges, checkpoint and resume guards, diagnostics, harness differences, and explicit verification limits.
- Keep provider/account routing, billing policy, and machine-specific capacity defaults out of the portable skill.
- Preserve existing concurrency, single-writer, loader, and example regression checks; extend synthetic offline documentation tests.

## [1.0.1] - 2026-09-24

Wording and consistency fixes; no new protocol sections.

- State the concurrency ceiling that batch dispatch must respect.
- Align the OMP mapping with the one-writer-per-file rule.
- Specify the untrusted-evidence rule in `SKILL.md`, where the README says it lives.
- Resolve the apparent conflict between producer/consumer leaves and "a dependent leaf waits".
- Make the rule that child agents skip project-wide checks unconditional.
- Drop a restated sentence from routing step 5.
- Test the frontmatter against common agent-skill loader limits.

## [1.0.0] - 2026-08-29

- First public release: routing pass, adaptive concurrency, capability
  routing, dispatch contract, integration gate and efficiency scorecard.

[1.7.1]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.5.2...v1.6.0
[1.5.2]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.0.1...v1.3.0
[1.0.1]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/tag/v1.0.0
