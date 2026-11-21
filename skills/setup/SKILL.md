---
name: setup
description: Find the Starfield install, the saves folder and the mod manager, save them as the plugin's path settings, and report which public modding tools are installed (with the install step for each missing one). Use on first use of this plugin, or when a tool or path seems missing.
---

# Setup

Finds the paths the other skills and the guard hooks need, and checks the tools. It only reads; the one file it writes is the settings file in step 6, after the user agrees.

## Steps

1. **Python.** Run `python --version` (on Linux or macOS also `python3 --version`). The plugin's hooks need Python 3.9 or newer; if it is missing, stop and tell the user to install it from python.org (on Windows, tick "Add python.exe to PATH"), then open a new window. Without Python the guard hooks refuse every tool call they cover, on purpose.

2. **The game.** Look in this order and list every copy found:
   - Steam: read `C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf` (each `"path"` entry is a library); the game is `<library>\steamapps\common\Starfield`.
   - Game Pass: `<drive>:\XboxGames\Starfield\Content` on each drive.
   - Linux (Steam with Proton): `~/.steam/steam/steamapps/common/Starfield` and the libraries in `~/.steam/steam/steamapps/libraryfolders.vdf`.

   The game folder is the one holding `Starfield.exe`; its `Data` folder holds `Starfield.esm`. Only the Steam copy has the Creation Kit's tools (`Tools\Papyrus Compiler\PapyrusCompiler.exe`, `Tools\Archive2\Archive2.exe`), which building scripts and archives needs. If there are several copies, ask the user which one they play.

3. **The saves folder.** Usually `Documents\My Games\Starfield\Saves`. When OneDrive has moved Documents, it is under `OneDrive\Documents\My Games\Starfield\Saves`; on Windows read the real Documents path with PowerShell `[Environment]::GetFolderPath('MyDocuments')`. A Game Pass copy keeps its saves in a container under `%LOCALAPPDATA%\Packages\BethesdaSoftworks.ProjectGold_*`. The load order the game reads is `%LOCALAPPDATA%\Starfield\Plugins.txt`.

4. **The mod manager.** Ask the user which one they use, then confirm it:
   - Mod Organizer 2: the instance folder holds `ModOrganizer.ini`, `mods\` and `profiles\` (portable instances sit next to `ModOrganizer.exe`; others are under `%LOCALAPPDATA%\ModOrganizer\Starfield`). MO2's `overwrite` folder is worth guarding.
   - Vortex: the staging folder is `%APPDATA%\Vortex\starfield\mods` unless the user changed it (Vortex: Settings, Mods, Mod Staging Folder). Worth guarding.
   - None (files copied by hand): say that a mod manager makes undoing a test much easier.

5. **The tools.** Run each check below and report a table: tool, found or not, version, and for a missing one the install line. The version the plugin was written against is in brackets; an older one may lack commands the skills use. Download pages are `https://github.com/taosecurity/<tool>/releases`; each tool's `AGENTS.md` has the full install steps.

   | Tool | Check | Needed for |
   |---|---|---|
   | sf-mod-check 0.9.0 | `sf-mod-check --version` | checking plugins, conflicts, release zips, triage |
   | sf-mod-build 0.1.1 | `sf-mod-build doctor` | building a mod from `sfmod.json` |
   | BuildKit 0.4.1 | a builder's `dotnet list package` shows `Taosecurity.Starfield.BuildKit` | writing plugins with Mutagen |
   | sf-pex-tools 0.1.0 | `python -I pex_compare.py --version` in its folder | comparing scripts, reading archives |
   | sf-load-order 0.1.1 | `sf-load-order.cmd --version` in its folder | load order checks |
   | sf-cut-check 0.1.9 | `sf-cut-check --version` | cut-content lookups (optional) |
   | sf-test-plan 0.2.0 | `python -I sf_test_plan.py --help` in its folder | test plans |
   | sf-papyrus-ref 0.1.0 | `python -I sf_papyrus_ref.py lookup Debug.Notification --no-local` in its folder | Papyrus lookups and the MCP server |
   | sf-patch-day 0.1.2 | `python -I sf-patch-day.py --version` in its folder | after a game update |
   | sf-log-collector 2.0.1 | `Collect-StarfieldTestLogs.ps1` exists in its folder | gathering test logs |
   | papyrus-log-check 0.3.2 | its `--version` | reading the Papyrus log |
   | sf-save-health 0.7.0 | `sf-save-health --help` (exit 3 is expected; it has no `--version`, and every report's first line names the version) | save checks after a test |
   | sf-save-reader 0.1.3 | `sf-save-reader --version` | quest stages in saves |

   Also report `dotnet --list-sdks` (sf-mod-build and BuildKit need .NET SDK 9 or later) and `git --version`.

6. **Save the settings.** Show the user what was found, then, with their OK, write the settings file:
   - Windows: `%APPDATA%\starfield-modding\starfield-modding.json`
   - Linux or macOS: `~/.config/starfield-modding/starfield-modding.json`

   ```json
   {
     "game_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Starfield",
     "saves_dir": "C:\\Users\\<you>\\Documents\\My Games\\Starfield\\Saves",
     "extra_guarded": ["C:\\Users\\<you>\\AppData\\Roaming\\Vortex\\starfield\\mods"],
     "papyrus_ref": "C:\\Tools\\sf-papyrus-ref-0.1.0",
     "mod_manager": {"kind": "vortex", "path": "C:\\Users\\<you>\\AppData\\Roaming\\Vortex\\starfield\\mods"}
   }
   ```

   `game_dir` is the folder holding `Starfield.exe`. `extra_guarded` lists more folders the guard hook protects. `papyrus_ref` is the folder holding `sf_papyrus_ref.py`. `mod_manager.kind` is `mo2`, `vortex` or `none`. Leave out what wasn't found. A project can override any key in its own `.claude/starfield-modding.json`, and environment variables (`SFMOD_GAME_DIR`, `SFMOD_SAVES_DIR`, `SFMOD_EXTRA_GUARDED`, `SF_PAPYRUS_REF`) override both.

7. **Report.** One short list: the game copy and its Data folder, the saves folder, the mod manager, the tools found and missing, and where the settings were saved. Say that the guard hook now refuses writes into the Data folder, the saves folder and `Plugins.txt`, and that the user installs mods with their mod manager.
