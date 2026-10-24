from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text()


class SkillContractTests(unittest.TestCase):
    def test_skill_has_portable_frontmatter(self) -> None:
        self.assertTrue(SKILL.startswith("---\n"))
        frontmatter = SKILL.split("---\n", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name: ultraterm-subagent-protocol$")
        self.assertRegex(frontmatter, r"(?m)^description: .+subagents")
        self.assertIn("acronym: USAP", frontmatter)

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
        self.assertLess(len(SKILL.encode()), 7_000)
        for forbidden in (
            "/Users/",
            "Liberty Design",
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
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("python3 -m unittest discover -s tests -v", readme)
        self.assertFalse(re.search(r"(?i)(api[_ -]?key|token)\s*[:=]\s*[^<{\[]", readme))

class ReleaseContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = (ROOT / "references/ultraterm.md").read_text()
        self.changelog = (ROOT / "CHANGELOG.md").read_text()

    def test_proposed_version_is_consistent_and_unreleased(self) -> None:
        version = re.search(r"(?m)^  version: (\d+\.\d+\.\d+)$", SKILL).group(1)
        self.assertEqual(version, "1.2.0")
        for text in (SKILL, self.mapping, self.changelog):
            self.assertIn(version, text)
            self.assertIn("Unreleased", text)
        self.assertIn("not yet released or runtime-verified", self.changelog)

    def test_host_budgets_are_explicit_and_bounded(self) -> None:
        for phrase in (
            "timeoutMs", "600,000 ms (10 minutes)", "28,800,000 ms (8 hours)",
            "including queue time", "maxTurns", "default 64", "maximum 2048",
            "maxRetries: 1", "compaction settings", "timeout ends observation only",
        ):
            self.assertIn(phrase, self.mapping)

    def test_recovery_and_delivery_do_not_imply_replay(self) -> None:
        for phrase in (
            "disk checkpoints", "explicit resume", "unfinished tasks only",
            "Never automatically replay", "idle boundary", "next user message",
        ):
            self.assertIn(phrase, SKILL)
        for phrase in (
            "memory-only", "do not provide daemon survival", "without replaying",
            "Completed tasks never repeat", "Healthy durable checkpoints",
            "diagnose", "checkpoint errors", "does not trigger a model turn",
        ):
            self.assertIn(phrase, self.mapping)

    def test_compatibility_and_public_disclosure(self) -> None:
        self.assertIn("telemetry remains numeric version 1 with additive fields", self.mapping)
        self.assertIn("No dependencies or provider routing changes", self.mapping)
        for path in ("README.md", "SKILL.md", "CHANGELOG.md", "references/ultraterm.md"):
            text = (ROOT / path).read_text()
            for forbidden in ("/Users/", "Liberty Design", "STRIPE_API_KEY", "OPENROUTER_API_KEY"):
                self.assertNotIn(forbidden, text, path)
            self.assertNotRegex(text, r"(?i)(12[- ]turn|30[- ]minute|30min)")


class ReadmeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readme = (ROOT / "README.md").read_text()

    def test_readme_version_matches_skill_frontmatter(self) -> None:
        frontmatter = SKILL.split("---\n", 2)[1]
        version = re.search(r"(?m)^  version: (\d+\.\d+\.\d+)$", frontmatter)
        self.assertIsNotNone(version, "SKILL.md must declare metadata.version")
        self.assertIn(f"(currently {version.group(1)})", self.readme)

    def test_readme_has_no_design_basis_section(self) -> None:
        self.assertNotRegex(self.readme, r"(?im)^#+ .*design basis")

    def test_readme_relative_links_resolve(self) -> None:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.readme):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()
