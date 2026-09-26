# Changelog

All notable changes to the UltraTerm Subagent Protocol are documented here.
The canonical version is `metadata.version` in [`SKILL.md`](SKILL.md) and
follows [Semantic Versioning](https://semver.org/).

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

[1.0.1]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/tag/v1.0.0
