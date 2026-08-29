# Contributing

Keep USAP vendor-neutral, compact enough to load at task start, and grounded in observable workflow outcomes.

1. Open an issue describing the failure mode or efficiency gap.
2. Change the smallest relevant section.
3. Add or update a deterministic test when the structural contract changes.
4. Run `python3 -m unittest discover -s tests -v`.
5. Submit a pull request with the behavior change and evidence.

Do not add provider credentials, personal paths, private workflows, generated transcripts, mandatory dependencies, or runtime-specific rules to `SKILL.md`. Put optional runtime mappings under `references/`.