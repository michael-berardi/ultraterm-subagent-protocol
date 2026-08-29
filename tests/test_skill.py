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
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("python3 -m unittest discover -s tests -v", readme)
        self.assertFalse(re.search(r"(?i)(api[_ -]?key|token)\s*[:=]\s*[^<{\[]", readme))


if __name__ == "__main__":
    unittest.main()
