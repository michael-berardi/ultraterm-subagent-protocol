"""Offline privacy guard for shipped text, installers, and skill instructions.

The portable release has no runtime code and no default configuration file.
These checks fail if telemetry tooling, remote assets, or network instructions
are added to the files a user installs or reads.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SHIPPED_FILES = (
    "README.md",
    "SKILL.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "references/omp.md",
    "references/ultraterm.md",
    "scripts/build-release.sh",
    "scripts/install.sh",
    "scripts/install.ps1",
)

# Instructions loaded by an agent at runtime; they must not initiate network use.
RUNTIME_FILES = ("SKILL.md", "references/omp.md", "references/ultraterm.md")

# Known analytics/telemetry SDKs, exporters and hosted collectors.
TELEMETRY = re.compile(
    r"(?i)"
    r"\b(posthog|sentry|segment|mixpanel|amplitude|datadog|bugsnag|"
    r"hotjar|fullstory|newrelic|plausible|umami)\b"
    r"|google[- ]?analytics|googletagmanager|gtag\.js"
    r"|opentelemetry[^\s,;]*exporter|otel[^\s,;]*exporter"
    r"|(api|cdn)\.(telemetry|analytics|tracking)"
)

# Third-party assets a docs viewer or UI would fetch without a user action.
REMOTE_ASSET_HOST = re.compile(
    r"(?i)https?://(img\.shields\.io|fonts\.googleapis\.com|fonts\.gstatic\.com"
    r"|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|unpkg\.com"
    r"|googletagmanager\.com|www\.google-analytics\.com)"
)

# Commands that would make the portable skill itself reach the network.
NETWORK_CALL = re.compile(
    r"(?i)"
    r"https?://|\bcurl\b|\bwget\b|invoke-webrequest|\birm\b|fetch\s*\("
    r"|\bgit\b[^\n]*\b(clone|pull|fetch)\b"
    r"|\bnpm\b|\bpnpm\b|\byarn\b|\bpip3?\s+install\b"
    r"|\burlsession\b|\bsocket\b"
)


class PrivacyContractTests(unittest.TestCase):
    def test_no_telemetry_packages_or_endpoints_in_shipped_files(self) -> None:
        hits = []
        for rel in SHIPPED_FILES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if TELEMETRY.search(line):
                    hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(hits, [], "Telemetry reintroduced in shipped files:\n" + "\n".join(hits))

    def test_skill_instructions_make_no_network_call(self) -> None:
        hits = []
        for rel in RUNTIME_FILES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if NETWORK_CALL.search(line):
                    hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(hits, [], "Network call in portable skill instructions:\n" + "\n".join(hits))

    def test_readme_loads_no_remote_assets(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"(?im)!\[[^\]]*\]\(https?://", readme),
            "README embeds a remote image",
        )
        self.assertIsNone(REMOTE_ASSET_HOST.search(readme), "README names a third-party asset host")

    def test_readme_privacy_section_answers_the_basic_questions(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Privacy\n", readme)
        section = readme.split("## Privacy", 1)[1].split("\n## ", 1)[0]
        for phrase in (
            "makes no network calls",
            "no telemetry",
            "Nothing is uploaded",
            "To remove it",
            "model provider",
        ):
            self.assertIn(phrase, section)


if __name__ == "__main__":
    unittest.main()
