"""Neutrality guard for shipped documentation.

USAP ships no built-in model id, provider default, fallback chain, paid-route
allowlist, or personal/project name. Those choices belong to the operator's
config and the host's own provider catalog. This test keeps the shipped docs
neutral.

Modeled on ~/dev/carl/test/neutrality.test.ts.
"""

import os
import re
import unittest

# Shipped documentation surfaces. LICENSE is deliberately excluded: it carries
# legal copyright attribution that must remain intact. Tests and fixtures are
# also excluded; they are not shipped to users.
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
    r"Mike|Berardi|Dana|Felix|acme|acme|Mouseia"
    r"|Liberty Design|libertydesign|acme|/Users/",
    re.IGNORECASE,
)


# The published repository path is the one place an owner name may appear:
# install commands and links must resolve. Placeholders such as `your-org`
# return 404 for anyone who copies them.
CANONICAL_REPO = "github.com/michael-berardi/ultraterm-subagent-protocol"
GITHUB_URL = re.compile(r"github\.com/[\w.-]+/ultraterm-subagent-protocol")


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

    def test_shipped_docs_have_no_model_ids_or_personal_names(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hits = []
        for rel_path in SHIPPED_FILES:
            path = os.path.join(root, rel_path)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    if MODEL_CHOICE.search(line) or PERSONAL.search(line.replace(CANONICAL_REPO.split("/", 1)[1], "")):
                        hits.append(f"{rel_path}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(
            hits,
            [],
            "Shipped docs contain model ids or personal names:\n" + "\n".join(hits),
        )


if __name__ == "__main__":
    unittest.main()
