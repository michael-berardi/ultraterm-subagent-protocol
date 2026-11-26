"""Offline privacy guard for shipped text, installers, the update helper, and skill instructions.

The skill text has no runtime code and no default configuration file; the only
shipped code that keeps state is the optional update.py, whose two cache files
are documented in PRIVACY.md. These checks fail if telemetry tooling, remote
assets, network instructions, or any other persistent write are added to the
files a user installs or reads.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SHIPPED_FILES = (
    "README.md",
    "PRIVACY.md",
    "SKILL.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/updates.md",
    "references/omp.md",
    "references/ultraterm.md",
    "update.py",
    "scripts/build-release.sh",
    "scripts/install.sh",
    "scripts/install.ps1",
)

# update.py's state, the only files USAP keeps outside the skill folder. Each one must
# appear in the PRIVACY.md local-write table with its bound; nothing else may be added.
UPDATE_STATE = ("usap/update.json", "usap/update.log")
DOCUMENTED_STATE = re.compile(r"(?:usap/)?update\.(?:json|log)\b")
# The platform cache folders those two files live in, exempt only on a line that
# names a documented file or goes through update.py's cache_dir().
CACHE_BASES = re.compile(r"cache_dir\(\)|~/Library/Caches|\$XDG_CACHE_HOME|~/\.cache")

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

# A new persistent artifact would need either a state-bearing path/name or a
# write call near a state word. Plain prose that says no such file is written
# deliberately does not match these patterns.
STATE_PATH = re.compile(
    r"""(?ix)
    [A-Za-z0-9_.$~{}-]*(?:/|\\)\s*(?:logs?|history|cache|transcripts?)(?:/|\\|$)
    | [A-Za-z0-9_.-]*\.(?:log|cache|history|transcript)\b
    | (?<![A-Za-z0-9_-])(?:LOG|HISTORY|CACHE|TRANSCRIPT)(?:_FILE|_PATH|_DIR)\b
    """
)
STATE_WRITE_CALL = re.compile(
    r"""(?ix)
    (?:\bopen\s*\(|\bwrite(?:_text|_bytes|file|line)?\s*\(|\btee\b
       |\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b
       |\bmkdir\b|\btouch\b|\bwritefile\b|\bfs\.write\b|>>?)
    [^\n]{0,160}\b(?:logs?|logging|history|cache|caches|transcript|transcripts)\b
    |
    \b(?:logs?|logging|history|cache|caches|transcript|transcripts)\b[^\n]{0,160}
    (?:\bopen\s*\(|\bwrite(?:_text|_bytes|file|line)?\s*\(|\btee\b
       |\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b
       |\bmkdir\b|\btouch\b|\bwritefile\b|\bfs\.write\b|>>?)
    """
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

    def privacy_section(self) -> str:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("\n## Privacy\n", readme)
        return readme.split("\n## Privacy\n", 1)[1].split("\n## ", 1)[0]

    def test_readme_privacy_is_a_short_summary_that_links_details(self) -> None:
        section = self.privacy_section()
        lines = [line.strip() for line in section.strip().splitlines() if line.strip()]
        self.assertTrue(3 <= len(lines) <= 6, f"Privacy has {len(lines)} lines; want 3-6")
        self.assertLessEqual(max(len(line) for line in lines), 120, "Privacy line too long")
        self.assertIn("[PRIVACY.md](PRIVACY.md)", lines[-1])
        for phrase in ("no network calls", "no telemetry", "anonymous", "at most daily",
                       "USAP_NO_UPDATE_CHECK=1", "Stored locally", "model provider", "To remove it"):
            self.assertIn(phrase, section)

    def test_docs_state_the_update_check_truthfully(self) -> None:
        # update.py checks for updates, so no doc may still claim there is no check.
        for rel in ("README.md", "PRIVACY.md", "docs/updates.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            for stale in ("No automatic update check", "never checks for updates", "never prompts you to update"):
                self.assertNotIn(stale, text, rel)

    def test_privacy_doc_carries_the_network_details(self) -> None:
        text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
        for phrase in (
            "makes no network calls",
            "sends no telemetry",
            "Nothing is uploaded",
            "api.github.com/repos/michael-berardi/ultraterm-subagent-protocol/releases/latest",
            "usap-update-check",
            "sends no identifier, installed version, usage data, or machine data",
            "at most once every 24 hours",
            "USAP_NO_UPDATE_CHECK=1",
            "--notify off",
            "model provider",
            "## Removal",
        ):
            self.assertIn(phrase, text)

    def test_privacy_doc_has_a_bounded_local_write_table(self) -> None:
        text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("writes no USAP logs, prompt history, transcripts, or credential files", text)
        for column in ("Local write", "Contents", "Lifetime", "Cleanup", "Deletion"):
            self.assertIn(column, text)
        rows = [line for line in text.splitlines() if line.startswith("| ")]
        for state in UPDATE_STATE + (".ultraterm-subagent-protocol.previous", "usap-update."):
            row = next((line for line in rows if state in line), "")
            self.assertTrue(row, f"{state} has no local-write table row")
            self.assertEqual(row.count(" | "), 4, row)
        self.assertIn("256 KB", next(line for line in rows if "usap/update.log" in line))

    def test_update_helper_keeps_only_the_documented_state(self) -> None:
        source = (ROOT / "update.py").read_text(encoding="utf-8")
        names = set(re.findall(r'cache_dir\(\) / "([^"]+)"', source))
        self.assertEqual({"usap/" + name for name in names}, set(UPDATE_STATE))
        self.assertIn("LOG_LIMIT = 256 * 1024", source)

    def test_no_log_history_or_cache_write_is_introduced(self) -> None:
        # Self-check keeps the detector from passing vacuously.
        for sample in (
            'echo x >> "$HOME/.usap.log"',
            'open("history.txt", "a")',
            "Set-Content cache.txt value",
            "mkdir -p ~/.cache/usap",
        ):
            self.assertTrue(
                STATE_PATH.search(sample) or STATE_WRITE_CALL.search(sample),
                sample,
            )
        self.assertTrue(STATE_PATH.search(CACHE_BASES.sub("", "mkdir -p ~/.cache/usap/history")))
        hits = []
        for rel in SHIPPED_FILES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            in_cache_dir = False
            for lineno, line in enumerate(text.splitlines(), 1):
                if rel == "update.py":
                    # The platform cache folder lookup; the files under it are pinned by
                    # test_update_helper_keeps_only_the_documented_state.
                    if line.startswith("def cache_dir("):
                        in_cache_dir = True
                        continue
                    if in_cache_dir and line and not line.startswith(" "):
                        in_cache_dir = False
                    if in_cache_dir:
                        continue
                if DOCUMENTED_STATE.search(line) or "cache_dir()" in line:
                    line = CACHE_BASES.sub("", DOCUMENTED_STATE.sub("", line))
                if STATE_PATH.search(line) or STATE_WRITE_CALL.search(line):
                    hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(
            hits, [],
            "Persistent log/history/cache write introduced:\n" + "\n".join(hits),
        )


if __name__ == "__main__":
    unittest.main()
