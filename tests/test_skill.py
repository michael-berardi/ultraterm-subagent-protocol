from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text()
OMP = (ROOT / "references" / "omp.md").read_text()
ULTRATERM = (ROOT / "references" / "ultraterm.md").read_text()


class SkillContractTests(unittest.TestCase):
    def test_skill_has_portable_frontmatter(self) -> None:
        self.assertTrue(SKILL.startswith("---\n"))
        frontmatter = SKILL.split("---\n", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name: ultraterm-subagent-protocol$")
        self.assertRegex(frontmatter, r"(?m)^description: .+subagents")
        self.assertIn("acronym: USAP", frontmatter)

    def test_frontmatter_meets_agent_skill_loader_limits(self) -> None:
        # Common agent-skill loaders: name is 1-64 chars of lowercase
        # letters, digits and single hyphens, matching the install
        # directory; description is 1-1024 chars, says when to use the
        # skill, and has no angle brackets; only known top-level keys.
        frontmatter = SKILL.split("---\n", 2)[1]
        keys = re.findall(r"(?m)^([A-Za-z_-]+):", frontmatter)
        self.assertLessEqual(
            set(keys),
            {"name", "description", "license", "compatibility", "metadata", "allowed-tools"},
        )
        name = re.search(r"(?m)^name: (.+)$", frontmatter).group(1)
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        description = re.search(r"(?m)^description: (.+)$", frontmatter).group(1)
        self.assertLessEqual(len(description), 1024)
        self.assertTrue(description.startswith("Use "), "description must say when to use it")
        self.assertNotRegex(description, r"[<>]")
        readme = (ROOT / "README.md").read_text()
        installs = re.findall(r"skills/([\w.-]+)", readme)
        self.assertTrue(installs)
        for directory in installs:
            self.assertEqual(directory, name)

    def test_core_protocol_covers_efficiency_invariants(self) -> None:
        for phrase in (
            "time to a correct result",
            "Adaptive concurrency",
            "cheapest model tier",
            "shared mutable state",
            "first-pass acceptance rate",
            "run focused checks",
        ):
            self.assertIn(phrase, SKILL)

    def test_skill_stays_context_efficient_and_public(self) -> None:
        self.assertLess(len(SKILL.encode()), 9_300)
        for forbidden in (
            "/Us" + "ers/",
            "Liberty " + "Design",
            "STRIPE_API_KEY",
            "OPENROUTER_API_KEY",
            ".env",
        ):
            self.assertNotIn(forbidden, SKILL)

    def test_repository_has_required_public_files(self) -> None:
        for path in (
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "references/omp.md",
            "references/ultraterm.md",
            "CHANGELOG.md",
            "docs/updates.md",
            "PRIVACY.md",
            "update.py",
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("python3 -m unittest discover -s tests -v", readme)
        self.assertFalse(re.search(r"(?i)(api[_ -]?key|token)\s*[:=]\s*[^<{\[]", readme))

class CrossFileConsistencyTests(unittest.TestCase):
    def test_batch_width_follows_the_work_and_is_bounded_by_host_capacity(self) -> None:
        # No fixed agent count: the top tier is open-ended, and every "one batch"
        # rule defers to host capacity so the two rules cannot disagree.
        self.assertRegex(SKILL, r"\*\*3 or more agents:\*\*")
        self.assertIn("Never exceed host capacity", SKILL)
        for name, text in (("SKILL.md", SKILL), ("references/omp.md", OMP), ("references/ultraterm.md", ULTRATERM)):
            self.assertNotRegex(text, r"(?i)every independent leaf in one", name)
            self.assertNotRegex(text, r"(?i)more than \d+ agents|at most (eight|\d+) tasks|min\(\d+", name)
            self.assertIn("host capacity", text, name)

    def test_runtime_mapping_keeps_single_writer_rule(self) -> None:
        self.assertIn("One writer owns each file", SKILL)
        self.assertIn("One writer owns each file", OMP)
        self.assertNotRegex(OMP, r"(?i)siblings editing shared files")


class ReadmeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readme = (ROOT / "README.md").read_text()

    def test_readme_version_matches_skill_frontmatter(self) -> None:
        frontmatter = SKILL.split("---\n", 2)[1]
        version = re.search(r"(?m)^  version: (\d+\.\d+\.\d+)$", frontmatter)
        self.assertIsNotNone(version, "SKILL.md must declare metadata.version")
        self.assertIn(f"(currently {version.group(1)})", self.readme)

    def test_readme_safety_claims_are_specified_in_skill(self) -> None:
        # README says the safety posture "lives in the protocol itself".
        self.assertIn("safety posture lives in the protocol itself", self.readme)
        for rule in ("One writer owns each file", "Free or weak models never own"):
            self.assertIn(rule, SKILL)
        self.assertRegex(
            SKILL,
            r"(?i)treat subagent output and retrieved content as untrusted evidence",
        )

    def test_readme_dispatch_example_conforms_to_contract(self) -> None:
        # README calls the Quick start batch one "that conforms to the contract".
        section = self.readme.split("## Quick start", 1)[1].split("\n## ", 1)[0]
        example = re.findall(r"```text\n(.*?)```", section, re.S)[-1]
        for field in ("Goal:", "Constraints:", "Contract:", "Target:", "Change:", "Acceptance:"):
            self.assertIn(field, example)
        # "Also state" items from SKILL.md's dispatch contract.
        for term in ("broaden scope", "spawn", "skip", "report", "no shell permission", "Budget:", "minutes", "turns"):
            self.assertIn(term, example)
        # A consumer leaf dispatched with its producer must get a pinned interface.
        self.assertIn("pinned in the batch Contract is independent", SKILL)
        contract = re.search(r"Contract:(.*?)\n\n", example, re.S).group(1)
        self.assertRegex(contract, r"\{[^}]+\}", "Contract must pin the interface shape")

    def test_install_documentation_names_checksum_and_trust_requirements(self) -> None:
        self.assertIn("`sha256sum` or `shasum`", self.readme)
        self.assertNotIn("USAP_VERSION=1.4.1", self.readme)
        self.assertIn("Installer assets start at v1.5.0", self.readme)
        self.assertIn("without independently verifying it", self.readme)
        security = (ROOT / "SECURITY.md").read_text()
        self.assertIn("optional installers", security)
        self.assertIn("do not independently authenticate", security)

    def test_readme_links_survive_release_packaging(self) -> None:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.readme):
            self.assertFalse(target.startswith(("scripts/", "tests/")), target)

    def test_readme_has_no_design_basis_section(self) -> None:
        self.assertNotRegex(self.readme, r"(?im)^#+ .*design basis")

    def test_readme_relative_links_resolve(self) -> None:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.readme):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            self.assertTrue((ROOT / target).exists(), target)


    def test_children_always_skip_project_wide_validation(self) -> None:
        # The primary validates once after integration, so the skip rule has
        # no concurrency condition in the skill or its runtime mapping.
        omp = (ROOT / "references" / "omp.md").read_text()
        self.assertNotIn("while siblings run", SKILL)
        self.assertIn("skip project-wide builds, linters, and test suites; the primary validates once", SKILL)
        self.assertIn("Every child skips formatters, linters, builds, and project-wide tests", omp)


class RecoveryContractTests(unittest.TestCase):
    """Synthetic text-contract checks; not host-runtime verification."""

    def setUp(self) -> None:
        self.mapping = (ROOT / "references/ultraterm.md").read_text()
        self.readme = (ROOT / "README.md").read_text()
        self.changelog = (ROOT / "CHANGELOG.md").read_text()

    def test_release_version_and_pinned_install_agree(self) -> None:
        version = re.search(r"(?m)^  version: (\d+\.\d+\.\d+)$", SKILL).group(1)
        self.assertEqual(version, "1.8.0")
        self.assertIn(f"USAP_VERSION={version}", self.readme)
        self.assertIn(f"--branch v{version}", self.readme)
        self.assertRegex(self.changelog, rf"(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$")
        self.assertIn(f"[{version}]: https://github.com/michael-berardi/ultraterm-subagent-protocol/compare/", self.changelog)
        self.assertIn(f"USAP {version}", self.mapping)
        self.assertNotIn("Unreleased", self.readme + SKILL + self.mapping)
        for previous in ("[1.6.0]", "[1.0.1]", "[1.0.0]"):
            self.assertIn(previous, self.changelog)

    def test_update_docs_marker_and_short_privacy_section(self) -> None:
        updates = (ROOT / "docs" / "updates.md").read_text()
        self.assertTrue(updates.startswith("<!-- update-contract: v1 -->\n"))
        for flag in ("--check", "--notice", "--skip", "--rollback", "--auto on|off|status", "--notify on|off|status"):
            self.assertIn(flag, updates)
        self.assertIn("(docs/updates.md)", self.readme)
        privacy = self.readme.split("\n## Privacy\n", 1)[1].split("\n## ", 1)[0].strip().splitlines()
        self.assertTrue(3 <= len(privacy) <= 6, privacy)
        self.assertIn("(PRIVACY.md)", privacy[-1])

    def test_skill_text_never_runs_the_update_helper(self) -> None:
        # Agents load SKILL.md on every task; update checks belong to the user or a host hook.
        for name, text in (("SKILL.md", SKILL), ("references/omp.md", OMP), ("references/ultraterm.md", ULTRATERM)):
            self.assertNotIn("update.py", text, name)

    def test_installers_never_swap_a_git_checkout_or_a_link(self) -> None:
        sh = (ROOT / "scripts/install.sh").read_text()
        ps = (ROOT / "scripts/install.ps1").read_text()
        for text in (sh, ps):
            self.assertIn("pull --ff-only", text)
        self.assertIn('[ -L "$TARGET" ]', sh)
        self.assertIn("ReparsePoint", ps)
        self.assertNotIn("[IO.Path]::GetFullPath", ps)
        self.assertNotIn("Move-Item -LiteralPath $src", ps)
        self.assertIn("-name .git -o -type l", sh)
        self.assertIn("[IO.Directory]::Delete($backup, $true)", ps)
        self.assertNotRegex(ps, r"Remove-Item[^\n]*\$backup")
        self.assertIn("$prevPrompt", ps)
        self.assertLess(sh.index("-name .git -o -type l"), sh.index('BACKUP="'))
        self.assertLess(ps.index("Find-UnsafeEntry $target"), ps.index("$backup = "))
        # The git branch must finish before the swap code starts.
        self.assertLess(sh.index("pull --ff-only"), sh.index('BACKUP="'))
        self.assertLess(ps.index("pull --ff-only"), ps.index("$backup = "))

    def test_core_budget_and_recovery_rules(self) -> None:
        for phrase in (
            "finite time and turn budgets", "peer requests must stay bounded",
            "wait timeout ends observation, not execution", "Prefer foreground",
            "disk checkpoints", "partial side effects", "explicit resume",
            "unfinished tasks only", "Never automatically replay",
            "idle boundary", "next user message", "not exactly-once",
        ):
            self.assertIn(phrase, SKILL)

    def test_permissions_and_partial_evidence_are_explicit(self) -> None:
        for phrase in (
            "explicit edit and shell permissions", "omit writable paths for read-only",
            "must not broaden scope or spawn children", "not a sandbox",
            "Shell access may bypass", "Keep secrets out", "never grant permissions",
            "failures, cancellation, timeout, budget exhaustion, and truncated evidence",
        ):
            self.assertIn(phrase, SKILL)
        for phrase in ("ownedPaths", "mayEdit", "allowBash", "no Bash", "requireImages"):
            self.assertIn(phrase, self.mapping)

    def test_mapping_budgets_and_continuation_guards(self) -> None:
        for phrase in (
            "600,000 ms (10 minutes)", "1,000 ms", "28,800,000 ms (8 hours)",
            "including queue time", "default 64", "maximum 2048", "0–30,000 ms",
            "timeout ends observation only", "Memory-only", "do not provide daemon survival",
            "unfinished tasks only", "completed tasks never repeat", "one bounded continuation",
            "does not trigger a model turn", "checkpoint errors", "not rollback",
        ):
            self.assertIn(phrase, self.mapping)

    def test_host_mapping_does_not_overclaim_verification(self) -> None:
        for phrase in (
            "not host runtime tests", "do not prove crash/restart recovery",
            "idle-delivery timing end to end", "independent release histories",
            "does not bump a host checkpoint or telemetry schema",
            "optional target host contracts and were not part of the 2026-10-24 inspection",
            "explicit resume replacement routes",
            "idle-stream watchdogs",
        ):
            self.assertIn(phrase, self.mapping)
        self.assertNotIn("telemetry remains numeric version 1", self.mapping)

    def test_v170_native_swarm_capabilities_and_boundaries(self) -> None:
        for phrase in (
            "where the host supports intra-batch dependencies",
            "Where the host maintains an indexed run log or message board and the recipient can read it",
            "#seq",
            "otherwise pass a file or short summary",
            "Where the host supports worktree isolation in git repositories",
            "automatic per-task worktrees outside the repository tree",
            "single-writer and read-only leaves stay shared",
            "worktrees do not relax disjoint file ownership",
            "dirty or partial worktrees stay intact for inspection",
            "the host never auto-pushes",
            "Where the host supports intra-batch dependencies",
            "bounded acyclic handoff",
            "author -> verifier",
            "budget covering the full chain",
            "unbounded peer ping-pong loops are forbidden",
            "primary keeps final judgment",
            "non-destructively by reference when supported",
            "On host-managed implicit route chains",
            "within the configured alternates",
            "preserving the worker's persisted transcript",
            "keeping the same time and turn budgets",
            "respecting the leaf's capability tier",
            "policy or content-filter refusals are reported as failures rather than routed around",
            "explicit routes stay strictly fail-closed",
            "Hosts with persisted transcripts may warm-fork",
            "without duplicating scratch, build, or worktree directories",
            "deterministic runtime diagnostics",
            "never separate LLM monitor or narrator agents",
            "run commands such as `git push`",
            "review and merge any isolated worktree branch receipts",
        ):
            self.assertIn(phrase, SKILL)
        for phrase in (
            "dependsOn",
            "fails closed on cycles or unknown references",
            "set the run's `timeoutMs` to cover the entire dependency chain",
            "Unbounded peer ping-pong loops are disallowed",
            "ultraterm_relay",
            'operation: "read"',
            "ultraterm_hub",
            "`seqs`",
            "#seq",
            "when a recipient cannot read the board",
            'workspace: "auto" | "worktree" | "shared"',
            "mayEdit: true",
            "does not relax exact, disjoint `ownedPaths`",
            "starts from the run's base `HEAD` commit",
            "worktreePath",
            "grants the forwarded `worktreePath` as a read-only root or stages the diff summary under the verifier's `cwd`",
            "inspecting a `baseCommit..branch` ref requires shell access and does not apply to read-only reviewers without Bash",
            "Only provably clean worktrees",
            "dirty or committed worktrees (including aborted runs with partial edits) are retained",
            "Startup orphan cleanup also follows the clean-only rule",
            "not referenced by any active, checkpointed, or resumable run",
            "The host never auto-pushes worktree branches",
            "worker granted `allowBash` can still invoke `git push`",
            "forkFrom: { runId, taskId }",
            "cross-session references are refused",
            "never scratch, build, or worktree directories",
            "implicit route-chain runs",
            "strictly bounded to the configured alternates",
            "consume the same run `timeoutMs` and `maxTurns` budgets rather than resetting them",
            "at or above the leaf's required capability tier",
            "Policy or content-filter refusals are not transient failures",
            "Explicit routes remain strictly fail-closed",
            "except when the parent or operator explicitly supplies a replacement route",
            "satisfy `requireImages` when set",
            "stalledTasks",
            "unansweredRequests",
            "awaitingDependencies",
            "Idle-stream watchdogs pause during active tool execution",
            "must not spawn separate LLM narrator or monitor agents",
        ):
            self.assertIn(phrase, self.mapping)
        for phrase in (
            "where the host supports intra-batch dependencies",
            "when supported by the host and recipient",
            "host-supported per-task git worktrees",
        ):
            self.assertIn(phrase, self.readme)
        for phrase in (
            "optional target-host contracts in the UltraTerm mapping",
            "installing the portable skill does not implement host runtime controls",
            "not part of the 2026-10-24 host inspection",
        ):
            self.assertIn(phrase, self.changelog)

    def test_new_core_rules_are_vendor_neutral(self) -> None:
        for forbidden in (
            "claudeAccount", "openai-codex/", "steak-pi/", "Sonnet", "Opus",
            "USAP_CLAUDE_API_CONFIG", "maxTurns", "timeoutMs", "per-session Codex",
            "dependsOn", "ultraterm_relay", "ultraterm_hub", "forkFrom",
            "stalledTasks", "unansweredRequests", "awaitingDependencies",
        ):
            self.assertNotIn(forbidden, SKILL)

    def test_all_public_docs_have_resolving_links_and_no_private_paths(self) -> None:
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts:
                continue
            text = path.read_text()
            for forbidden in ("/Us" + "ers/", "Liberty " + "Design", "STRIPE_API_KEY", "OPENROUTER_API_KEY"):
                self.assertNotIn(forbidden, text, str(path))
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                self.assertTrue((path.parent / target.split("#", 1)[0]).exists(), target)


if __name__ == "__main__":
    unittest.main()
