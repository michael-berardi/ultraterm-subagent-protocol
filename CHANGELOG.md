# Changelog

All notable changes to the UltraTerm Subagent Protocol are documented here.
The canonical version is `metadata.version` in [`SKILL.md`](SKILL.md) and
follows [Semantic Versioning](https://semver.org/).

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

[1.4.0]: https://github.com/your-org/ultraterm-subagent-protocol/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/your-org/ultraterm-subagent-protocol/compare/v1.0.1...v1.3.0
[1.0.1]: https://github.com/your-org/ultraterm-subagent-protocol/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/your-org/ultraterm-subagent-protocol/releases/tag/v1.0.0
