"""Neutrality guard for shipped documentation.

USAP ships no built-in model id, provider default, fallback chain, paid-route
allowlist, or personal/project name. Those choices belong to the operator's
config and the host's own provider catalog. This test keeps the shipped docs
neutral.

Modeled on ~/dev/carl/test/neutrality.test.ts.
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

# Shipped documentation surfaces. LICENSE is deliberately excluded: it carries
# legal copyright attribution that must remain intact. Personal checks additionally
# cover tests and docs, excluding this test itself.
SHIPPED_FILES = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "references/omp.md",
    "references/ultraterm.md",
]

# Concrete model ids that only an operator should choose. Provider-adapter code
# may name its own provider catalog, but no adapter files exist in this
# documentation-only repository.
MODEL_CHOICE = re.compile(
    r"gpt-[56][a-z0-9.-]*|deepseek[a-z0-9.-]*|opencode-go/|openrouter/|:exacto"
    r"|mimo-v[0-9][a-z0-9.-]*|glm-[0-9][a-z0-9.-]*|claude-[a-z0-9.-]*-5-5"
    r"|(haiku|sonnet|opus)[ -]?5[.-]5",
    re.IGNORECASE,
)

# Names of people and organisations: never in the shipped docs. `/Users/` is a
# machine-local path marker and also must not leak into public text.
PERSONAL = re.compile(
    r"Mike|Berardi|Felix|Mouseia"
    r"|Liberty Design|libertydesign|/Users/",
    re.IGNORECASE,
)


# The published repository path is the one place an owner name may appear:
# install commands and links must resolve. Placeholders such as `your-org`
# return 404 for anyone who copies them.
CANONICAL_REPO = "github.com/michael-berardi/ultraterm-subagent-protocol"
GITHUB_URL = re.compile(r"github\.com/[\w.-]+/ultraterm-subagent-protocol")


def load_private_terms(path=None):
    path = Path(path) if path is not None else Path(
        os.environ.get("OSS_PRIVATE_TERMS", "~/.config/oss-audit/names.txt")
    ).expanduser()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    terms = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    alternatives = []
    for term in terms:
        alternatives.append((r"(?<!\w)" if re.match(r"\w", term[0]) else "")
                            + re.escape(term)
                            + (r"(?!\w)" if re.match(r"\w", term[-1]) else ""))
    return re.compile("|".join(alternatives), re.IGNORECASE) if alternatives else None


def personal_files(root):
    for rel_path in SHIPPED_FILES:
        path = root / rel_path
        if path.is_file():
            yield path
    seen = set()
    for name in ("tests", "test", "Tests", "docs"):
        base = root / name
        if not base.is_dir() or (base.stat().st_dev, base.stat().st_ino) in seen:
            continue
        seen.add((base.stat().st_dev, base.stat().st_ino))
        for path in base.rglob("*"):
            rel = path.relative_to(root)
            if (path.is_file() and not path.samefile(__file__)
                    and path.suffix not in {".pyc", ".pyo", ".so", ".dylib"}):
                yield path


class NeutralityTests(unittest.TestCase):
    def test_shipped_github_urls_name_the_published_repo(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bad = []
        for rel_path in SHIPPED_FILES:
            path = os.path.join(root, rel_path)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    for url in GITHUB_URL.findall(line):
                        if url != CANONICAL_REPO:
                            bad.append(f"{rel_path}:{lineno}: {url}")
        self.assertEqual(bad, [], "Shipped GitHub URLs must name the published repo:\n" + "\n".join(bad))

    def test_shipped_docs_have_no_model_ids(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hits = []
        for rel_path in SHIPPED_FILES:
            path = os.path.join(root, rel_path)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    if MODEL_CHOICE.search(line):
                        hits.append(f"{rel_path}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(
            hits,
            [],
            "Shipped docs contain model ids or personal names:\n" + "\n".join(hits),
        )

    def test_no_personal_names(self):
        root = Path(__file__).resolve().parents[1]
        private = load_private_terms()
        hits = []
        for path in personal_files(root):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                line = line.replace(CANONICAL_REPO.split("/", 1)[1], "")
                if PERSONAL.search(line) or (private and private.search(line)):
                    hits.append(f"{path.relative_to(root)}:{lineno}")
        self.assertEqual(hits, [], "Personal names found in: " + ", ".join(hits))

    def test_private_terms_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            terms = Path(tmp) / "terms.txt"
            terms.write_text("# comment\n\nzzqx-private-term\n", encoding="utf-8")
            pattern = load_private_terms(terms)
            sample = Path(tmp) / "sample.txt"
            sample.write_text("A ZZQX-private-term here", encoding="utf-8")
            self.assertIsNotNone(pattern.search(sample.read_text(encoding="utf-8")))
            sample.write_text("ordinary text", encoding="utf-8")
            self.assertIsNone(pattern.search(sample.read_text(encoding="utf-8")))
            self.assertIsNone(pattern.search("xzzqx-private-term"))


if __name__ == "__main__":
    unittest.main()
