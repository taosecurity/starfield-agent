"""Tests for hooks/guard_game.py (DESIGN.md section 8.1): each case sends a tool call as JSON on stdin and
expects exit 2 (refused) or 0 (let through).

Run: python -I tests/test_guard_game.py   (or through selftest.py)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "hooks" / "guard_game.py"

STEAM_DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Starfield\Data"
OTHER_LIBRARY_DATA = r"E:\SteamLibrary\steamapps\common\Starfield\Data"
GAMEPASS_DATA = r"D:\XboxGames\Starfield\Content\Data"
SAVES = r"C:\Users\Someone\Documents\My Games\Starfield\Saves"
ONEDRIVE_SAVES = r"C:\Users\Someone\OneDrive\Documents\My Games\Starfield\Saves"
GAMEPASS_SAVES = r"C:\Users\Someone\AppData\Local\Packages\BethesdaSoftworks.ProjectGold_3275kfvn8vcwc\SystemAppData\wgs"
PLUGINS_TXT = r"C:\Users\Someone\AppData\Local\Starfield\Plugins.txt"
PROJECT = r"C:\Users\Someone\Mods\MyMod"


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user_config = os.path.join(self.tmp.name, "user.json")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("SFMOD_", "SF_PAPYRUS_REF", "CLAUDE_PLUGIN_OPTION_", "CLAUDE_PROJECT_DIR"))}
        self.env["SFMOD_USER_CONFIG"] = self.user_config
        self.env["CLAUDE_PROJECT_DIR"] = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_guard(self, tool, tool_input, cwd=PROJECT):
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": cwd}
        proc = subprocess.run([sys.executable, "-I", str(GUARD)], input=json.dumps(payload).encode("utf-8"),
                              capture_output=True, env=self.env, timeout=30)
        return proc.returncode, proc.stderr.decode("utf-8", errors="replace")

    def refused(self, tool, tool_input, cwd=PROJECT):
        code, err = self.run_guard(tool, tool_input, cwd)
        self.assertEqual(code, 2, f"expected a refusal for {tool} {tool_input}; stderr: {err}")
        self.assertIn("starfield-agent guard", err)
        return err

    def allowed(self, tool, tool_input, cwd=PROJECT):
        code, err = self.run_guard(tool, tool_input, cwd)
        self.assertEqual(code, 0, f"expected {tool} {tool_input} to pass; stderr: {err}")

    def bash(self, command, cwd=PROJECT):
        return {"command": command}


class FileTools(GuardCase):
    def test_write_into_steam_data_refused(self):
        err = self.refused("Write", {"file_path": STEAM_DATA + r"\MyMod.esm", "content": "x"})
        self.assertIn("Data folder", err)

    def test_write_into_other_steam_library_refused(self):
        self.refused("Write", {"file_path": OTHER_LIBRARY_DATA + r"\MyMod.esm", "content": "x"})

    def test_edit_in_gamepass_data_refused(self):
        self.refused("Edit", {"file_path": GAMEPASS_DATA + r"\Scripts\MyScript.pex", "old_string": "a", "new_string": "b"})

    def test_write_into_saves_refused(self):
        self.refused("Write", {"file_path": SAVES + r"\Save1.sfs", "content": "x"})

    def test_write_into_onedrive_saves_refused(self):
        self.refused("Write", {"file_path": ONEDRIVE_SAVES + r"\Save1.sfs", "content": "x"})

    def test_write_into_gamepass_saves_refused(self):
        self.refused("Write", {"file_path": GAMEPASS_SAVES + r"\container.1", "content": "x"})

    def test_edit_plugins_txt_refused(self):
        self.refused("Edit", {"file_path": PLUGINS_TXT, "old_string": "a", "new_string": "b"})

    def test_notebook_in_data_refused(self):
        self.refused("NotebookEdit", {"notebook_path": STEAM_DATA + r"\x.ipynb", "new_source": "x"})

    def test_mixed_slashes_and_case_refused(self):
        self.refused("Write", {"file_path": "c:/program files (x86)/STEAM/SteamApps/Common/starfield/DATA/x.esm"})

    def test_dotdot_into_data_refused(self):
        self.refused("Write", {"file_path": STEAM_DATA.replace(r"\Data", r"\Tools\..\Data") + r"\x.esm"})

    def test_dotdot_out_of_data_allowed(self):
        self.allowed("Write", {"file_path": STEAM_DATA + r"\..\MyNotes.txt"})

    def test_project_file_allowed(self):
        self.allowed("Write", {"file_path": PROJECT + r"\Builder\Program.cs", "content": "x"})

    def test_similar_name_allowed(self):
        self.allowed("Write", {"file_path": r"C:\Mods\steamapps\common\Starfield\DataBackup\x.esm"})

    def test_settings_file_adds_folder(self):
        staging = r"C:\Users\Someone\AppData\Roaming\Vortex\starfield\mods"
        with open(self.user_config, "w", encoding="utf-8") as f:
            json.dump({"extra_guarded": [staging]}, f)
        self.refused("Write", {"file_path": staging + r"\MyMod\MyMod.esm"})
        self.allowed("Write", {"file_path": PROJECT + r"\x.txt"})

    def test_project_settings_moved_install(self):
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "starfield-agent.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"G:\Games\Starfield"}, f)
        self.refused("Write", {"file_path": r"G:\Games\Starfield\Data\x.esm"})

    def test_old_project_settings_file_still_read(self):
        # 0.1.0 called the plugin starfield-modding; its project file is read when the new one is missing.
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "starfield-modding.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"G:\Games\Starfield"}, f)
        self.refused("Write", {"file_path": r"G:\Games\Starfield\Data\x.esm"})

    def test_old_and_new_project_files_guard_together(self):
        # A new file must not hide folders the old one guards (no layer takes a guarded folder away).
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "starfield-modding.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"G:\Games\Starfield", "extra_guarded": [r"D:\MO2\overwrite"]}, f)
        with open(os.path.join(self.tmp.name, ".claude", "starfield-agent.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"K:\Other\Starfield"}, f)
        self.refused("Write", {"file_path": r"K:\Other\Starfield\Data\x.esm"})
        self.refused("Write", {"file_path": r"G:\Games\Starfield\Data\x.esm"})
        self.refused("Write", {"file_path": r"D:\MO2\overwrite\x.esp"})

    def test_old_project_file_still_cannot_set_papyrus_ref(self):
        sys.path.insert(0, str(ROOT / "hooks"))
        try:
            import sfmod_config
            os.makedirs(os.path.join(self.tmp.name, ".claude"))
            with open(os.path.join(self.tmp.name, ".claude", "starfield-modding.json"), "w", encoding="utf-8") as f:
                json.dump({"papyrus_ref": r"C:\Evil"}, f)
            names = ["CLAUDE_PROJECT_DIR", "SF_PAPYRUS_REF"]
            names += [k for k in os.environ if k.startswith(("SFMOD_", "CLAUDE_PLUGIN_OPTION_"))]
            saved = {k: os.environ.get(k) for k in names + ["SFMOD_USER_CONFIG"]}
            for k in names:
                os.environ.pop(k, None)
            os.environ["SFMOD_USER_CONFIG"] = self.user_config
            try:
                settings, _, problems = sfmod_config.load_settings(self.tmp.name)
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            self.assertNotIn("papyrus_ref", settings)
            self.assertTrue(any("ignored papyrus_ref" in p for p in problems))
        finally:
            sys.path.remove(str(ROOT / "hooks"))

    def test_env_var_saves_dir(self):
        self.env["SFMOD_SAVES_DIR"] = r"F:\Backup\Saves"
        self.refused("Write", {"file_path": r"F:\Backup\Saves\x.sfs"})

    def test_plugin_option_game_dir(self):
        self.env["CLAUDE_PLUGIN_OPTION_GAME_DIR"] = r"H:\SF"
        self.refused("Write", {"file_path": r"H:\SF\Data\x.esm"})

    def test_bad_input_fails_closed(self):
        proc = subprocess.run([sys.executable, "-I", str(GUARD)], input=b"not json", capture_output=True,
                              env=self.env, timeout=30)
        self.assertEqual(proc.returncode, 2)


class UserFileName(unittest.TestCase):
    """The user's settings file: starfield-agent.json, else the 0.1.0 starfield-modding.json in the same place."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "hooks"))
        import sfmod_config
        self.cfg = sfmod_config
        self.tmp = tempfile.TemporaryDirectory()
        names = ["APPDATA", "HOME", "USERPROFILE", "CLAUDE_PROJECT_DIR", "SF_PAPYRUS_REF"]
        names += [k for k in os.environ if k.startswith(("SFMOD_", "CLAUDE_PLUGIN_OPTION_"))]
        self.saved = {k: os.environ.get(k) for k in names}
        for k in names:
            os.environ.pop(k, None)
        os.environ["APPDATA"] = self.tmp.name
        os.environ["HOME"] = os.environ["USERPROFILE"] = self.tmp.name
        self.base = self.tmp.name if os.name == "nt" else os.path.join(self.tmp.name, ".config")

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        sys.path.remove(str(ROOT / "hooks"))
        self.tmp.cleanup()

    def write(self, name, data):
        folder = os.path.join(self.base, name)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_paths_new_name_first(self):
        self.assertEqual(self.cfg._user_config_paths(),
                         [os.path.join(self.base, "starfield-agent", "starfield-agent.json"),
                          os.path.join(self.base, "starfield-modding", "starfield-modding.json")])

    def test_old_file_read_when_new_is_missing(self):
        self.write("starfield-modding", {"papyrus_ref": r"C:\Tools\ref"})
        settings, sources, _ = self.cfg.load_settings(self.tmp.name)
        self.assertEqual(settings.get("papyrus_ref"), r"C:\Tools\ref")
        self.assertIn("starfield-modding.json", sources["papyrus_ref"])

    def test_users_new_file_beats_projects_old_file(self):
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "starfield-modding.json"), "w", encoding="utf-8") as f:
            json.dump({"mod_manager": {"kind": "mo2"}}, f)
        self.write("starfield-agent", {"mod_manager": {"kind": "vortex"}})
        settings, _, _ = self.cfg.load_settings(self.tmp.name)
        self.assertEqual(settings["mod_manager"]["kind"], "vortex")

    def test_new_value_wins_and_old_folders_still_guarded(self):
        self.write("starfield-modding", {"papyrus_ref": r"C:\Old", "extra_guarded": [r"D:\MO2\overwrite"]})
        self.write("starfield-agent", {"papyrus_ref": r"C:\New", "game_dir": r"G:\SF"})
        settings, _, _ = self.cfg.load_settings(self.tmp.name)
        self.assertEqual(settings.get("papyrus_ref"), r"C:\New")
        roots = [r for _, r in self.cfg.guarded_roots(settings, self.tmp.name)]
        self.assertTrue(any(r.endswith("mo2/overwrite") for r in roots), roots)
        self.assertTrue(any(r.endswith("g:/sf/data") for r in roots), roots)


class ShellTools(GuardCase):
    def test_mod_check_on_data_allowed(self):
        self.allowed("Bash", self.bash(f'sf-mod-check check --data "{STEAM_DATA}" MyMod.esm'))

    def test_python_tool_on_data_allowed(self):
        self.allowed("PowerShell", {"command": f'python -I C:\\Tools\\sf_papyrus_ref.py check "{STEAM_DATA}\\Scripts"'})

    def test_dir_data_allowed(self):
        self.allowed("PowerShell", {"command": f'dir "{STEAM_DATA}"'})

    def test_ls_pipe_filter_allowed(self):
        self.allowed("Bash", self.bash(f'ls "{STEAM_DATA}" | grep -i mymod | wc -l'))

    def test_get_childitem_select_allowed(self):
        self.allowed("PowerShell", {"command": f'Get-ChildItem "{STEAM_DATA}" -Filter *.esm | Select-Object Name'})

    def test_stderr_to_null_allowed(self):
        self.allowed("Bash", self.bash(f'ls "{STEAM_DATA}" 2>/dev/null'))

    def test_dir_redirect_refused(self):
        self.refused("PowerShell", {"command": f'dir "{STEAM_DATA}" > out.txt'})

    def test_copy_into_data_refused(self):
        self.refused("PowerShell", {"command": f'copy x.esm "{STEAM_DATA}"'})

    def test_ls_then_rm_refused(self):
        self.refused("Bash", self.bash(f'ls "{STEAM_DATA}"; rm "{STEAM_DATA}\\x.esm"'))

    def test_pipe_to_remove_item_refused(self):
        self.refused("PowerShell", {"command": f'Get-ChildItem "{STEAM_DATA}" | Remove-Item'})

    def test_out_file_refused(self):
        self.refused("PowerShell", {"command": f'Get-Content a.txt | Out-File "{PLUGINS_TXT}"'})

    def test_git_bash_drive_path_refused(self):
        self.refused("Bash", self.bash("cp x.esm '/c/Program Files (x86)/Steam/steamapps/common/Starfield/Data/'"))

    def test_escaped_spaces_refused(self):
        self.refused("Bash", self.bash(r"rm /c/Users/Someone/Documents/My\ Games/Starfield/Saves/x.sfs"))

    def test_env_var_path_refused(self):
        self.env["LOCALAPPDATA"] = r"C:\Users\Someone\AppData\Local"
        self.refused("PowerShell", {"command": r'Set-Content "$env:LOCALAPPDATA\Starfield\Plugins.txt" "*x.esm"'})

    def test_dotdot_in_command_refused(self):
        self.refused("Bash", self.bash(f'rm "{STEAM_DATA}\\..\\Data\\x.esm"'))

    def test_command_substitution_refused(self):
        self.refused("Bash", self.bash(f'ls "{STEAM_DATA}" $(rm -rf x)'))

    def test_tool_write_mode_refused(self):
        self.refused("Bash", self.bash(f'sf-mod-check fix --data "{STEAM_DATA}"'))

    def test_tool_out_into_data_refused(self):
        self.refused("Bash", self.bash(f'sf-load-order --out "{STEAM_DATA}\\report"'))

    def test_tool_out_elsewhere_allowed(self):
        self.allowed("Bash", self.bash(f'sf-cut-check scan --data "{STEAM_DATA}" --out C:\\Temp\\cutscan'))

    def test_unrelated_command_allowed(self):
        self.allowed("Bash", self.bash("rm -rf build && dotnet build"))

    def test_cwd_inside_data(self):
        self.allowed("Bash", self.bash("ls -la"), cwd=STEAM_DATA)
        self.refused("Bash", self.bash("rm x.esm"), cwd=STEAM_DATA)
        self.refused("Bash", self.bash("sf-load-order"), cwd=STEAM_DATA)

    def test_quoted_separator_not_split(self):
        self.allowed("Bash", self.bash(f'grep "a;b" "{STEAM_DATA}\\x.txt"'))

    def test_settings_folder_in_command_refused(self):
        with open(self.user_config, "w", encoding="utf-8") as f:
            json.dump({"extra_guarded": [r"D:\MO2\overwrite"]}, f)
        self.refused("Bash", self.bash(r"rm D:\MO2\overwrite\x.esp"))
        self.allowed("Bash", self.bash(r"ls D:\MO2\overwrite"))


GAME_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Starfield"


class ReviewFixes(GuardCase):
    """Cases found by the 0.1.0 code review (NOTES.md, "Reviews")."""

    def test_relative_data_from_game_root_refused(self):
        self.refused("Bash", self.bash("rm -rf Data"), cwd=GAME_ROOT)
        self.refused("PowerShell", self.bash("Remove-Item Data -Recurse"), cwd=GAME_ROOT)

    def test_cd_into_data_then_delete_refused(self):
        self.refused("Bash", self.bash("cd Data && del Starfield.esm"), cwd=GAME_ROOT)
        self.refused("PowerShell", self.bash("Set-Location Data; Remove-Item Starfield.esm"), cwd=GAME_ROOT)

    def test_cd_into_data_then_read_allowed(self):
        self.allowed("Bash", self.bash("cd Data && ls"), cwd=GAME_ROOT)

    def test_parent_of_data_refused_for_writes_only(self):
        self.refused("Bash", self.bash(f'rm -rf "{GAME_ROOT}"'))
        self.refused("Bash", self.bash(r'rm -rf "C:\Users\Someone\Documents\My Games\Starfield"'))
        self.allowed("Bash", self.bash(f'ls "{GAME_ROOT}"'))

    def test_wildcard_into_data_refused(self):
        data = os.path.join(self.tmp.name, "steamapps", "common", "Starfield", "Data")
        os.makedirs(data)
        open(os.path.join(data, "x.esm"), "w").close()
        pattern = os.path.join(self.tmp.name, "steamapps", "common", "Starfield", "Dat*", "x.esm").replace("\\", "/")
        self.refused("Bash", self.bash(f'rm "{pattern}"'))

    def test_tool_in_data_cwd_refused_even_when_naming_data(self):
        self.refused("Bash", self.bash(f'sf-load-order --data "{STEAM_DATA}"'), cwd=STEAM_DATA)

    def test_script_block_refused(self):
        self.refused("PowerShell", self.bash(
            f'Get-ChildItem "{STEAM_DATA}" -Filter *.esm | Where-Object {{ $_.Delete() }}'))
        self.refused("PowerShell", self.bash(f'(Get-Item "{STEAM_DATA}\\x.esm").Delete()'))
        self.refused("PowerShell", self.bash(f'Get-Content "{STEAM_DATA}\\x.txt" | % {{ [IO.File]::Delete($_) }}'))

    def test_uniq_and_ba2_extract_no_longer_read_only(self):
        self.refused("Bash", self.bash(f'uniq "{STEAM_DATA}\\a.txt" "{STEAM_DATA}\\b.txt"'))
        self.refused("Bash", self.bash(f'ba2-extract extract "{STEAM_DATA}\\x.ba2"'))

    def test_public_tool_commands_read_only(self):
        """sf-pex-tools' own commands (pex_compare.py, ba2_extract.py) and the new --version words may read the Data folder."""
        self.allowed("Bash", self.bash(f'python -I pex_compare.py dump "{STEAM_DATA}\\x.pex"'))
        self.allowed("Bash", self.bash(f'python -I pex_compare.py compare "{STEAM_DATA}\\a.ba2" "{STEAM_DATA}\\b.ba2"'))
        self.allowed("Bash", self.bash("python -I ba2_extract.py where"))
        self.allowed("Bash", self.bash("sf-save-health --version"))
        self.allowed("Bash", self.bash("python -I sf_test_plan.py --version"))
        self.allowed("Bash", self.bash("python -I sf_papyrus_ref.py list"))
        self.refused("Bash", self.bash(f'python -I ba2_extract.py extract "{STEAM_DATA}\\x.ba2"'))
        self.refused("Bash", self.bash(f'python -I pex_compare.py dump "{STEAM_DATA}\\x.pex" --out "{STEAM_DATA}\\y.txt"'))

    def test_save_tools_never_write_into_saves(self):
        """sf-save-reader extract writes a file and sf-save-health solo --reports writes a folder: never into the saves."""
        self.env["SFMOD_SAVES_DIR"] = SAVES
        self.allowed("Bash", self.bash(f'sf-save-reader quests "{SAVES}\\a.sfs" --data --details'))
        self.allowed("Bash", self.bash(f'sf-save-reader compare "{SAVES}\\a.sfs" "{SAVES}\\b.sfs"'))
        self.allowed("Bash", self.bash(f'sf-save-health solo --before "{SAVES}\\a.sfs" --after "{SAVES}\\b.sfs" --reports C:\\Reports'))
        self.refused("Bash", self.bash(f'sf-save-reader extract "{SAVES}\\a.sfs" "{SAVES}\\a.bin"'))
        self.refused("Bash", self.bash(f'sf-save-health solo C:\\Logs\\StarfieldLogs-1.zip --reports "{SAVES}\\r"'))
        self.refused("Bash", self.bash(f'sf-save-health solo C:\\Logs\\StarfieldLogs-1.zip --reports="{SAVES}\\r"'))
        # --opt="a path with spaces" is one word, so its value is checked like --opt "a path with spaces"
        self.refused("Bash", self.bash(f'python -I pex_compare.py dump C:\\Mods\\x.pex --out="{STEAM_DATA}\\y.txt"'))
        self.allowed("Bash", self.bash(f'python -I pex_compare.py dump "{STEAM_DATA}\\x.pex" --out="C:\\My Reports\\y.txt"'))

    def test_project_file_cannot_unguard_user_install(self):
        with open(self.user_config, "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"G:\Games\Starfield", "extra_guarded": [r"D:\MO2\overwrite"]}, f)
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "starfield-agent.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"C:\nowhere", "extra_guarded": []}, f)
        self.refused("Write", {"file_path": r"G:\Games\Starfield\Data\x.esm"})
        self.refused("Write", {"file_path": r"D:\MO2\overwrite\x.esp"})
        self.refused("Write", {"file_path": r"C:\nowhere\Data\x.esm"})

    def test_placeholder_option_does_not_hide_user_file(self):
        with open(self.user_config, "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"H:\SF"}, f)
        self.env["CLAUDE_PLUGIN_OPTION_GAME_DIR"] = "${user_config.game_dir}"
        self.refused("Write", {"file_path": r"H:\SF\Data\x.esm"})

    def test_hook_log(self):
        log = os.path.join(self.tmp.name, "hook.log")
        self.env["SFMOD_HOOK_LOG"] = log
        self.refused("Write", {"file_path": STEAM_DATA + r"\x.esm"})
        self.allowed("Bash", self.bash(f'ls "{STEAM_DATA}"'))
        with open(log, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("refused", text)
        self.assertIn("named=", text)


if __name__ == "__main__":
    unittest.main()
