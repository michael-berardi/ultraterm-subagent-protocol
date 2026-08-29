# UltraTerm Subagent Protocol (USAP)

A compact, vendor-neutral skill for getting more correct work done with subagents: faster wall-clock completion, less frontier-context pollution, lower total cost, and fewer rework loops.

USAP keeps the primary agent responsible for decomposition, judgment, integration, and proof. It delegates only bounded independent leaves, adapts concurrency to the dependency graph, routes each leaf to the cheapest capable model tier, and validates once after integration.

## Install

Copy this repository into a skill directory recognized by your agent runtime:

```sh
git clone https://github.com/michael-berardi/ultraterm-subagent-protocol.git \
  ~/.config/agents/skills/ultraterm-subagent-protocol
```

The installed path must contain `SKILL.md`. UltraTerm bundles and manages the same skill automatically for Auto sessions.

For project-local installation, copy the repository to your runtime's project skill directory, commonly `.agents/skills/ultraterm-subagent-protocol` or `.claude/skills/ultraterm-subagent-protocol`.

## Use

Load USAP at the start of a nontrivial task, before deciding whether to delegate:

```text
Use the UltraTerm Subagent Protocol for this task.
```

The protocol is tool-neutral. [`references/omp.md`](references/omp.md) maps it to OMP's `task` and `hub` tools.

## Design basis

USAP synthesizes the strongest recurring practices from:

- [OpenAI Codex subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents.md): keep the primary context focused, prefer read-heavy parallel leaves, use explicit model tiers, and treat write-heavy concurrency carefully.
- [Anthropic subagents](https://code.claude.com/docs/en/sub-agents): isolate context, specialize tools and prompts, and use cheaper models for bounded work.
- [Anthropic agent teams](https://code.claude.com/docs/en/agent-teams): use teams only for independent work because coordination and token costs rise materially.
- [Anthropic, Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents): prefer simple composable patterns and use orchestrator-worker workflows when decomposition cannot be fixed in advance.
- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system): scale parallelism to task breadth, write precise delegation prompts, and let a lead agent synthesize.
- [obra/superpowers parallel-agent skill](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md): one focused agent per independent problem domain and explicit integration review.

USAP intentionally rejects patterns that inflate work without evidence: delegating trivial tasks, assigning the top-level plan to a blank worker, mandatory reviewer chains for every small edit, parallel edits to shared files, and maximizing agent count as an end in itself.

## Validate

```sh
python3 -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).