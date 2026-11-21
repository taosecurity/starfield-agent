"""Tests for hooks/guard_game_code.py (DESIGN.md section 8.1). Each test builds a small git repo in a temporary
folder and sends a git or gh command as a hook call: exit 2 = refused, "ask" in the JSON = the user is asked,
exit 0 with no output = let through.

Run: python -I tests/test_guard_game_code.py   (or through selftest.py)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "hooks" / "guard_game_code.py"

OWN_SCRIPT = "Scriptname MyMod_QuestScript extends Quest\n\nFunction Log(string s)\n    Debug.Trace(\"[MyMod] \" + s)\nEndFunction\n"
CHAMPOLLION = ";/ Decompiled by Champollion V1.0.1\nSource   : SomeScript.psc\n/;\nScriptName SomeScript extends Quest\n"
GHIDRA = ("/* WARNING: Could not recover jumptable at 0x1400 */\n\nundefined8 FUN_14012ab30(longlong param_1)\n"
          "{\n  FUN_1401bc220(DAT_145e3a0b8);\n  return 0;\n}\n")
NOTES_ABOUT_GHIDRA = "# Notes\n\nI used Ghidra to read the format of the save header; the field list is below.\n"


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
                   check=True, capture_output=True)


class CodeGuardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "MyMod")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        self.write("README.md", "# MyMod\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "first")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("SFMOD_", "SF_PAPYRUS_REF", "CLAUDE_PLUGIN_OPTION_", "CLAUDE_PROJECT_DIR"))}
        self.env["SFMOD_USER_CONFIG"] = os.path.join(self.tmp.name, "user.json")
        self.env["CLAUDE_PROJECT_DIR"] = self.repo
        # A stand-in for sf-papyrus-ref: `script <name>` exits 0 for "ObjectReference", else 1.
        fake = os.path.join(self.tmp.name, "fakeref")
        os.makedirs(fake)
        with open(os.path.join(fake, "sf_papyrus_ref.py"), "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(0 if sys.argv[1:3] == ['script', 'ObjectReference'] else 1)\n")
        self.fake_ref = fake

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def stage(self, rel, text="x"):
        self.write(rel, text)
        git(self.repo, "add", "-f", rel)

    def run_guard(self, command, tool="Bash"):
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command},
                   "cwd": self.repo}
        proc = subprocess.run([sys.executable, "-I", str(GUARD)], input=json.dumps(payload).encode("utf-8"),
                              capture_output=True, env=self.env, timeout=60)
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")

    def refused(self, command, tool="Bash", contains=None):
        code, out, err = self.run_guard(command, tool)
        self.assertEqual(code, 2, f"expected a refusal for `{command}`; stdout {out} stderr {err}")
        if contains:
            self.assertIn(contains, err)

    def asked(self, command):
        code, out, err = self.run_guard(command)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def allowed(self, command, tool="Bash"):
        code, out, err = self.run_guard(command, tool)
        self.assertEqual((code, out.strip()), (0, ""), f"expected `{command}` to pass; stderr {err}")


class Commits(CodeGuardCase):
    def test_staged_official_plugin_refused(self):
        self.stage("Data/Starfield.esm")
        self.refused('git commit -m "add"', contains="Starfield.esm")

    def test_staged_dlc_plugin_and_archive_refused(self):
        self.stage("SFBGS003.esm")
        self.refused("git commit -m x")
        git(self.repo, "rm", "-q", "--cached", "SFBGS003.esm")
        self.stage("Starfield - Textures01.ba2")
        self.refused("git commit -m x", contains="archive")

    def test_official_psc_name_refused(self):
        self.env["SF_PAPYRUS_REF"] = self.fake_ref
        self.stage("Scripts/Source/ObjectReference.psc", "Scriptname ObjectReference extends Form\n")
        self.refused("git commit -m x", contains="official script")

    def test_creation_kit_base_folder_refused_without_tool(self):
        self.stage("Scripts/Source/Base/SQ_ParentScript.psc", "Scriptname SQ_ParentScript extends Quest\n")
        self.refused("git commit -m x", contains="Scripts/Source/Base")

    def test_ghidra_project_refused(self):
        self.stage("re/Starfield.gpr")
        self.refused("git commit -m x", contains="Ghidra")

    def test_ghidra_rep_folder_refused(self):
        self.stage("re/Starfield.rep/idata/00/x.prp")
        self.refused("git commit -m x", contains=".rep")

    def test_save_refused(self):
        self.stage("tests/Save1.sfs")
        self.refused("git commit -m x", contains="save")

    def test_decompiler_banner_asks(self):
        self.stage("Scripts/Source/SomeScript.psc", CHAMPOLLION)
        self.asked("git commit -m x")

    def test_ghidra_output_asks(self):
        self.stage("notes/function.c", GHIDRA)
        self.asked("git commit -m x")

    def test_own_psc_allowed(self):
        self.env["SF_PAPYRUS_REF"] = self.fake_ref
        self.stage("Scripts/Source/MyMod_QuestScript.psc", OWN_SCRIPT)
        self.allowed('git commit -m "add my script"')

    def test_notes_that_mention_ghidra_allowed(self):
        self.stage("NOTES.txt", NOTES_ABOUT_GHIDRA)
        self.allowed("git commit -m notes")

    def test_commit_all_sees_tracked_changes(self):
        self.stage("Starfield - Interface.ba2", "a")
        git(self.repo, "commit", "-q", "-m", "oops")
        self.write("Starfield - Interface.ba2", "b")
        self.refused('git commit -am "update"')

    def test_powershell_and_git_dash_c(self):
        self.stage("Constellation.esm")
        other = self.tmp.name
        payload_cmd = f'git -C "{self.repo}" commit -m x'
        code, out, err = self.run_guard(payload_cmd, tool="PowerShell")
        self.assertEqual(code, 2, err)
        self.assertTrue(os.path.isdir(other))


class AddsAndPushes(CodeGuardCase):
    def test_add_dot_with_official_file_refused(self):
        self.write("OldMars.esm", "x")
        self.refused("git add .")

    def test_add_named_save_refused(self):
        self.write("Quick.sfs", "x")
        self.refused("git add Quick.sfs && git commit -m x")

    def test_add_own_files_allowed(self):
        self.write("Scripts/Source/MyMod_QuestScript.psc", OWN_SCRIPT)
        self.allowed("git add -A")

    def test_push_with_official_file_in_history_refused(self):
        self.stage("ShatteredSpace.esm")
        git(self.repo, "commit", "-q", "-m", "oops")
        git(self.repo, "rm", "-q", "ShatteredSpace.esm")
        git(self.repo, "commit", "-q", "-m", "remove it again")
        self.refused("git push -u origin main", contains="in commit")

    def test_push_clean_history_allowed(self):
        self.stage("Scripts/Source/MyMod_QuestScript.psc", OWN_SCRIPT)
        git(self.repo, "commit", "-q", "-m", "script")
        self.allowed("git push origin main")

    def test_unrelated_command_ignored(self):
        self.stage("Starfield.esm")
        self.allowed("git status")


class Releases(CodeGuardCase):
    def make_zip(self, name, members):
        path = os.path.join(self.repo, name)
        with zipfile.ZipFile(path, "w") as z:
            for member, text in members.items():
                z.writestr(member, text)
        return name

    def test_release_zip_with_official_archive_refused(self):
        z = self.make_zip("MyMod-0.1.0.zip", {"MyMod.esm": "x", "Starfield - Main.ba2": "x"})
        self.refused(f'gh release create v0.1.0 {z} --title "MyMod 0.1.0" --notes-file notes.md',
                     contains="Starfield - Main.ba2")

    def test_release_zip_with_decompiled_script_asks(self):
        z = self.make_zip("MyMod-0.1.0.zip", {"MyMod.esm": "x", "Scripts/Source/Some.psc": CHAMPOLLION})
        self.asked(f"gh release upload v0.1.0 {z}")

    def test_release_own_zip_allowed(self):
        z = self.make_zip("MyMod-0.1.0.zip", {"MyMod.esm": "x", "MyMod - Main.ba2": "x", "README.md": "# MyMod"})
        self.allowed(f'gh release create v0.1.0 "{z}#MyMod 0.1.0" -R someone/MyMod --notes "First release."')

    def test_gist_of_executable_refused(self):
        self.write("CreationKit.exe", "x")
        self.refused("gh gist create CreationKit.exe --desc test")

    def test_gist_of_script_sources_zip_refused(self):
        self.write("ContentResources.zip", "x")
        self.refused("gh gist create ContentResources.zip")


if __name__ == "__main__":
    unittest.main()
