"""Checks for the plugin's skills (DESIGN.md section 8.1).

- every skills/<name>/SKILL.md has frontmatter whose name equals its folder, and a description under 400 characters;
- every public tool a skill names with a version uses the version in tests/tool_versions.json;
- no file in the repo carries private text (our own folder and account names).

Run: python -I tests/test_skills.py   (or through selftest.py)
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# All twelve skills from DESIGN.md section 3; every one is required.
ALL_SKILLS = [
    "setup", "new-mod", "build-mod", "rebuild-mod", "evaluate-mod", "test-plan",
    "log-review", "release-check", "patch-day", "logging-rules", "game-code-rules", "wrap-up",
]
REQUIRED = ALL_SKILLS

MAX_DESCRIPTION = 400

# Private text that must never appear in the public repo. The words are split so this file doesn't match itself.
PRIVATE_PATTERNS = [
    re.compile(re.escape("claude" + "projects"), re.I),
    re.compile(re.escape("Starfield " + "Dev"), re.I),
    re.compile(re.escape("Starfield " + "Scratch"), re.I),
    re.compile(re.escape("taosecurity" + "@"), re.I),
    re.compile(re.escape("\\" + "rb" + "\\"), re.I),
    re.compile(re.escape("From" + "RB"), re.I),
    re.compile(r"\b" + "P" + "UB" + r"\b"),
]
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".yml", ".yaml", ".toml", ".cmd", ".ps1", ".sh", ""}


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields, text[end + 5:]


def tool_versions():
    data = json.loads((ROOT / "tests" / "tool_versions.json").read_text(encoding="utf-8"))
    return data["tools"]


class SkillFiles(unittest.TestCase):
    def skill_dirs(self):
        return sorted(p for p in SKILLS.iterdir() if p.is_dir())

    def test_required_skills_exist(self):
        for name in REQUIRED:
            self.assertTrue((SKILLS / name / "SKILL.md").is_file(), f"missing skills/{name}/SKILL.md")

    def test_no_unplanned_skills(self):
        for d in self.skill_dirs():
            self.assertIn(d.name, ALL_SKILLS, f"skills/{d.name} is not in DESIGN.md's list (add it to ALL_SKILLS)")

    def test_frontmatter(self):
        for d in self.skill_dirs():
            path = d / "SKILL.md"
            self.assertTrue(path.is_file(), f"{d} has no SKILL.md")
            fields, body = read_frontmatter(path)
            self.assertIsNotNone(fields, f"{path}: no frontmatter (--- lines) at the top")
            self.assertEqual(fields.get("name"), d.name, f"{path}: frontmatter name must be {d.name!r}")
            desc = fields.get("description", "")
            self.assertTrue(desc, f"{path}: empty description")
            self.assertLess(len(desc), MAX_DESCRIPTION, f"{path}: description is {len(desc)} characters")
            self.assertIn("Use ", desc, f"{path}: description should say when to use the skill")
            self.assertRegex(body, r"(?m)^1\. ", f"{path}: no numbered steps")

    def test_tool_versions(self):
        versions = tool_versions()
        names = sorted(versions, key=len, reverse=True)
        pattern = re.compile(
            r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) + r") (\d+\.\d+\.\d+)(?![\w.])"
        )
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            for m in pattern.finditer(text):
                tool, version = m.group(1), m.group(2)
                self.assertEqual(
                    version, versions[tool],
                    f"{path.relative_to(ROOT)}: names {tool} {version}, but tool_versions.json says {versions[tool]}",
                )


class PrivateText(unittest.TestCase):
    def test_no_private_text(self):
        hits = []
        for path in sorted(ROOT.rglob("*")):
            if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for pat in PRIVATE_PATTERNS:
                    if pat.search(line):
                        hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:100]}")
        self.assertEqual(hits, [], "private text found:\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main(verbosity=2)
