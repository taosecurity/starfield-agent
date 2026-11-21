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
        self.assertIn("starfield-modding guard", err)
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
        with open(os.path.join(self.tmp.name, ".claude", "starfield-modding.json"), "w", encoding="utf-8") as f:
            json.dump({"game_dir": r"G:\Games\Starfield"}, f)
        self.refused("Write", {"file_path": r"G:\Games\Starfield\Data\x.esm"})

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


if __name__ == "__main__":
    unittest.main()
