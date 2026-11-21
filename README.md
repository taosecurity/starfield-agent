# starfield-agent

starfield-agent is a Claude Code plugin that teaches your AI assistant how to make Starfield mods the careful way.
It adds twelve skills (start, build, rebuild, evaluate, test and release a mod), two guard hooks that keep the
assistant out of your game's `Data` and saves folders and keep Bethesda's files out of your commits, and a Papyrus
lookup server, all built on free public modding tools.

Install it from inside Claude Code with these two commands:

```
/plugin marketplace add taosecurity/starfield-agent
/plugin install starfield-agent@starfield-agent
```

Then run the first-use skill, which finds your game, your saves and your mod manager and checks which tools you have:

```
/starfield-agent:setup
```

For AI assistants: step-by-step instructions are in [AGENTS.md](AGENTS.md).

Until version 0.2.0 this plugin was called starfield-modding. If you installed it under that name:

1. Remove it with `/plugin uninstall starfield-modding@starfield-modding`, then remove its marketplace with
   `/plugin marketplace remove starfield-modding`.
2. Install starfield-agent with the commands above.
3. If you set plugin options for the old plugin (game folder, saves folder, sf-papyrus-ref folder), set them again
   with `/plugin configure starfield-agent@starfield-agent`. Options don't move to the new name.

Your settings files keep working: the old `starfield-modding.json` files are still read (see
[Settings](#settings) for the rules).

## Example

The guard hook refuses a write into the game's `Data` folder, and lets a read-only check of the same folder through
(each line is one hook call, as Claude Code makes it; exit 2 means refused):

```
> python -I hooks/guard_game.py < write-into-data.json
starfield-agent guard: refused to change C:/Program Files (x86)/Steam/steamapps/common/Starfield/Data/MyMod.esm, because it is in the game's Data folder (Steam).
Copy the file in yourself or install it with your mod manager; the agent only reads these folders. To guard more folders or point at a moved install, see the starfield-agent README, "Settings".
exit 2

> python -I hooks/guard_game.py < sf-mod-check-on-data.json
exit 0
```

The plugin's own self-test, run from the plugin folder:

```
> python -I selftest.py
..............................................................................................................
----------------------------------------------------------------------
Ran 110 tests in 12.836s

OK
selftest: 110 tests, OK
Validating marketplace manifest: ...\starfield-agent\.claude-plugin\marketplace.json
...
✔ Validation passed
selftest: claude plugin validate OK
RESULT: OK
```

## What you get

| Skill | Use it when |
|---|---|
| `setup` | First use, or a tool or path seems missing. Finds the game, saves and mod manager, saves the settings, lists the tools. |
| `new-mod` | You want to start a new mod. Picks safe names and makes the project folder, git, notes and a builder. |
| `build-mod` | You want a test zip. Compiles Papyrus (optimize, never release), writes the plugin, packs and checks it. |
| `rebuild-mod` | You want to fix or remake another author's mod. Permission first, then proper code and credit. |
| `evaluate-mod` | You want to know what a mod does, or what changed in an update, and whether it touches your mods. |
| `test-plan` | Before a test session. Writes a plan for a new character with log checks. |
| `log-review` | After a test session. Reads the logs and drafts a result per mod. |
| `release-check` | Before an upload to Nexus Mods or Bethesda Creations. You do the upload yourself. |
| `patch-day` | After a game update. Checks SFSE plugins, your mods and your load order. |
| `logging-rules` | Writing or reviewing Papyrus. `Debug.Trace` lines, a debug option and README logging text. |
| `game-code-rules` | Before any commit, release or post that carries code. What may and may never be shared. |
| `wrap-up` | End of a session. Updates `NOTES.md` and commits finished work. |

Call a skill by name, such as `/starfield-agent:build-mod`, or just ask ("build my mod"); the assistant loads the
matching skill by itself.

Two hooks run before every file edit and shell command:

- **The Data and saves guard** refuses any change to the game's `Data` folder, the saves folder, `Plugins.txt` and
  `ContentCatalog.txt`. Plain reading commands and the read-only modes of the modding tools still work there.
- **The game-code guard** refuses `git add`, `git commit`, `git push`, `gh release` and `gh gist` when they would carry
  official plugins or archives, the game or Creation Kit executables, official script sources, saves, or Ghidra and IDA
  databases. It asks you first when a file looks like decompiler output.

The **papyrus-ref MCP server** lets the assistant look up Papyrus functions and events with
[sf-papyrus-ref](https://github.com/taosecurity/sf-papyrus-ref) instead of recalling them from memory.

## Install

You need [Claude Code](https://code.claude.com) (written against 2.1.330) and Python 3.9 or newer, because the hooks
are small Python scripts.

If you don't have it, install the current Python 3 from [python.org](https://www.python.org/downloads/). On the first screen of the
installer, tick **Add python.exe to PATH**. To check that it worked, open a new Command Prompt and type
`python --version`. It should print a version number.

Then, inside Claude Code, run the two `/plugin` commands at the top of this page. From a terminal the same is:

```
claude plugin marketplace add taosecurity/starfield-agent
claude plugin install starfield-agent@starfield-agent
```

To see what it added, run `claude plugin details starfield-agent@starfield-agent` (it lists the twelve skills,
the hooks and the MCP server). Restart Claude Code, then run `/starfield-agent:setup`. If Python is missing, the guard hooks refuse every call they
cover, on purpose, so install Python first.

## The modding tools

The skills call these free tools. None of them is needed to install the plugin; the `setup` skill tells you which
ones are missing and how to get each one. Versions are the ones the skills were written against.

- [sf-mod-check](https://github.com/taosecurity/sf-mod-check) 0.9.0: checks plugins, conflicts and release zips.
- [sf-mod-build](https://github.com/taosecurity/sf-mod-build) 0.1.1 and [BuildKit](https://github.com/taosecurity/BuildKit) 0.4.2: build a mod.
- [sf-pex-tools](https://github.com/taosecurity/sf-pex-tools) 0.1.0: compares compiled scripts and reads archives.
- [sf-load-order](https://github.com/taosecurity/sf-load-order) 0.1.1: checks a load order.
- [sf-cut-check](https://github.com/taosecurity/sf-cut-check) 0.1.9: finds cut content (optional).
- [sf-test-plan](https://github.com/taosecurity/sf-test-plan) 0.2.0: writes test plans.
- [sf-papyrus-ref](https://github.com/taosecurity/sf-papyrus-ref) 0.1.0: Papyrus lookups and the MCP server.
- [sf-patch-day](https://github.com/taosecurity/sf-patch-day) 0.1.3: checks mods after a game update.
- [sf-log-collector](https://github.com/taosecurity/sf-log-collector) 2.0.1 and [papyrus-log-check](https://github.com/taosecurity/papyrus-log-check) 0.3.2: gather and read test logs.
- [sf-save-health](https://github.com/taosecurity/sf-save-health) 0.7.1 and [sf-save-reader](https://github.com/taosecurity/sf-save-reader) 0.1.3: check saves after a test.

## Words used here

- **Plugin:** a mod's data file (`.esm`, `.esp` or `.esl`). It adds or changes records in the game. (Claude Code
  also calls its add-ons "plugins"; this README says "the plugin" for starfield-agent itself.)
- **Load order:** the order the game loads plugins in. When two plugins change the same record, the one loaded later wins.
- **Papyrus:** Starfield's scripting language. Scripts are written as `.psc` source files and compiled into `.pex`
  files that the game runs.
- **BA2:** Bethesda's archive format. Mods pack their scripts, models and textures into `.ba2` files.
- **SFSE:** the Starfield Script Extender, which loads `.dll` plugins that add features the game lacks.
- **Creation Kit (CK):** Bethesda's official editor for making Starfield mods.
- **Skill:** a set of instructions the assistant loads when a task matches it.
- **Hook:** a small program Claude Code runs before a tool call; it can refuse the call.
- **MCP (Model Context Protocol):** a standard way for AI assistants to call a tool.

## Settings

The guard knows the usual folders by their shape, wherever they are: any Steam library's
`steamapps\common\Starfield\Data`, Game Pass `XboxGames\Starfield\Content\Data` on any drive,
`Documents\My Games\Starfield\Saves` (also under OneDrive and in a Proton prefix), the Game Pass save container
`%LOCALAPPDATA%\Packages\BethesdaSoftworks.ProjectGold_*`, and `%LOCALAPPDATA%\Starfield\Plugins.txt`. Settings are
only needed for a moved install, for extra folders, and to name the sf-papyrus-ref folder.

Each setting is read from the first place that has it:

1. Environment variables: `SFMOD_GAME_DIR`, `SFMOD_SAVES_DIR`, `SFMOD_EXTRA_GUARDED` (folders separated by `;`) and
   `SF_PAPYRUS_REF`.
2. The plugin's options, which Claude Code offers when you enable the plugin: game folder, saves folder and
   sf-papyrus-ref folder. They reach the guard hooks and the papyrus-ref MCP server. To set them without the
   dialog, run `claude plugin configure starfield-agent@starfield-agent` to see them, and pipe a JSON object
   such as `{"papyrus_ref": "C:\\Tools\\sf-papyrus-ref-0.1.0"}` into the same command with `--values-stdin`.
3. The project's `.claude/starfield-agent.json`. It can't set `papyrus_ref`, because that setting names a program
   to run and a project you download could ship its own file; the guard ignores it there and says so.
4. Your own `starfield-agent.json`: `%APPDATA%\starfield-agent\` on Windows, `~/.config/starfield-agent/`
   on Linux and macOS. The `setup` skill writes this file after you agree.

   Until 0.2.0 the plugin was called starfield-modding. The old `starfield-modding.json` next to each file is read too, after both new files: its guarded folders add up with the rest (to unguard a folder, remove it from the old file too, or delete the old file), and its other values count only where neither new file sets them. A project's old file can't set `papyrus_ref` either.

The folder settings (`game_dir`, `saves_dir`, `extra_guarded`) add up instead: every folder named in any of these
places is guarded, so a project's settings file can add folders but never take one away. An empty option, or one
still showing a placeholder such as `${user_config.papyrus_ref}`, counts as not set.

The settings file looks like this (leave out what you don't need):

```json
{
  "game_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Starfield",
  "saves_dir": "C:\\Users\\<you>\\Documents\\My Games\\Starfield\\Saves",
  "extra_guarded": ["C:\\Users\\<you>\\AppData\\Roaming\\Vortex\\starfield\\mods"],
  "papyrus_ref": "C:\\Tools\\sf-papyrus-ref-0.1.0",
  "mod_manager": {"kind": "vortex", "path": "C:\\Users\\<you>\\AppData\\Roaming\\Vortex\\starfield\\mods"}
}
```

- `game_dir`: the folder holding `Starfield.exe`. Its `Data` folder is guarded.
- `saves_dir`: a saves folder in an unusual place. It is guarded.
- `extra_guarded`: more folders to guard, such as Vortex's staging folder (`%APPDATA%\Vortex\starfield\mods` unless
  you changed it) or Mod Organizer 2's `overwrite` folder.
- `papyrus_ref`: the folder holding `sf_papyrus_ref.py`, for the MCP server and the official-script check.
- `mod_manager`: `{"kind": "mo2" | "vortex" | "none", "path": ...}`, used by the skills.

With Mod Organizer 2, the real `Data` folder stays clean because MO2 shows the game a virtual one; the guard still
covers the real one. With Vortex, you drop the finished zip onto Vortex yourself.

## The Papyrus lookup server

Download [sf-papyrus-ref](https://github.com/taosecurity/sf-papyrus-ref/releases), unzip it, and put its folder in the
settings file (`papyrus_ref`) or in the `SF_PAPYRUS_REF` environment variable. Restart Claude Code; `/mcp` then lists
`papyrus-ref` with four tools such as `papyrus_lookup`.

Without sf-papyrus-ref, the server still starts but offers one tool, `papyrus_setup_help`, which tells the assistant
where to get it. Check what the launcher finds with:

```
> python -I mcp/papyrus_ref_launcher.py --find
papyrus-ref launcher: found C:\Tools\sf-papyrus-ref-0.1.0\sf_papyrus_ref.py (from environment variable SF_PAPYRUS_REF)
C:\Python313\python.exe -I C:\Tools\sf-papyrus-ref-0.1.0\sf_papyrus_ref.py mcp --quiet
```

(Folder names changed.) It exits 0 when it finds the tool and 1 when it doesn't (`not found`).

## Troubleshooting

- **A refused call:** the hooks write their reason to Claude Code (stderr), starting with `starfield-agent guard:`.
  The assistant sees it and tells you. Start Claude Code with `claude --debug` to see every hook run.
- **The guards' log:** set the environment variable `SFMOD_HOOK_LOG` to a file path (for example
  `C:\Users\<you>\sfmod-hooks.log`) before you start Claude Code. Each hook run then adds lines saying what command
  it read, which guarded folders it found in it, and what it decided. It is off when the variable is unset.
- **Linux and macOS:** the hooks and the server run `python`. If your system has only `python3`, install the
  package that provides `python` (on Ubuntu and Debian, `python-is-python3`) or make a `python` link to `python3`.
  Without it the hooks can't start.
- **The MCP server:** run `python -I mcp/papyrus_ref_launcher.py --find` in the plugin folder (Claude Code keeps a copy
  under `~/.claude/plugins/cache/starfield-agent/starfield-agent/<version>`). Add `--log <file>` to copy the launcher's messages to a file. `/mcp` shows whether the
  server is connected.
- **A guard refuses something it shouldn't:** please open an issue with the command. Meanwhile you can run `/plugin`
  and disable starfield-agent.
- **Check the plugin itself:** `python -I selftest.py` in the plugin folder runs all tests and
  `claude plugin validate .`; add `--verbose` for each test's name, or `--no-claude` on a machine without Claude Code.

Limits: a shell guard reads the command's text. It follows `cd` and `Set-Location`, resolves relative paths and
wildcards, and refuses commands that name a guarded folder and run code inside the command (PowerShell `{ }` blocks,
`(...)` expressions and `.Method()` calls). A path built while the command runs (a variable set in one part and used
in the next, or a script file the command runs) still isn't seen. Edits through the file tools have no such gap. When
the game-code guard can't list the files a `git` command would send, it asks you instead of letting it through.

## Found a mistake?

Open an issue: https://github.com/taosecurity/starfield-agent/issues

## Credits

Made by Richard Bejtlich. The folder layout (the repo root as both the marketplace and the plugin) follows
[universal-modder](https://github.com/rehan-remade/universal-modder) by rehan-remade and
[bgs-modding-superpowers](https://github.com/BB-84C/bgs-modding-superpowers) by BB-84C, both MIT licensed. No code or
text was taken from either. The skills call the public tools listed above. Claude Code is made by Anthropic.

## License

MIT. See [LICENSE](LICENSE).
