# AGENTS.md: starfield-modding 0.1.0

Instructions for an AI assistant that installs or uses this plugin. Plain numbered steps; every command here has been run once.

## 1. What it is and when to use it

1. starfield-modding is a Claude Code plugin (and its own plugin marketplace) for Starfield mod authors.
2. It adds twelve skills: `setup`, `new-mod`, `build-mod`, `rebuild-mod`, `evaluate-mod`, `test-plan`, `log-review`, `release-check`, `patch-day`, `logging-rules`, `game-code-rules` and `wrap-up`. They are called as `/starfield-modding:<skill>`, and Claude Code also loads them when a task matches.
3. It adds two PreToolUse hooks: `guard_game.py` (refuses changes to the game's `Data` folder, the saves folder, `Plugins.txt` and `ContentCatalog.txt`) and `guard_game_code.py` (refuses `git add|commit|push`, `gh release create|upload` and `gh gist create` that would carry Bethesda's files or code).
4. It registers one MCP server, `papyrus-ref`, which runs sf-papyrus-ref when it is installed and a help-only stub when it is not.
5. Use it when the user makes, rebuilds, evaluates, tests or releases Starfield mods with Claude Code. Don't use it for other games.

## 2. Prerequisites

1. Claude Code 2.1.330 or newer (`claude --version`). The hooks use `"onFailure": "block"`, which needs 2.1.295 or newer.
2. Python 3.9 or newer on PATH as `python` (`python --version`). Standard library only; nothing to `pip install`.
3. git, for the game-code guard and the skills that commit.
4. Optional, for the skills: the public tools listed in the README ("The modding tools"), at the versions given there, and the .NET SDK 9 or newer for sf-mod-build and BuildKit. The `setup` skill checks all of them.

## 3. Install

1. From a terminal:

       claude plugin marketplace add taosecurity/starfield-modding
       claude plugin install starfield-modding@starfield-modding

2. Or inside a Claude Code session: `/plugin marketplace add taosecurity/starfield-modding`, then `/plugin install starfield-modding@starfield-modding`.
3. From a local clone instead of GitHub: `claude plugin marketplace add <path to the clone>`, then the same install command.
4. Restart Claude Code so the skills, hooks and MCP server load.

## 4. Prove the install

1. Run `claude plugin list`. The output lists `starfield-modding@starfield-modding` with `Status: ✔ enabled`. (`claude plugin install` also says when the three optional options are not set yet; that is normal.)
2. In the plugin folder (or a clone), run `python -I selftest.py`. The last line is `RESULT: OK` (exit 0). On a machine without Claude Code on PATH, use `python -I selftest.py --no-claude`.

## 5. Common tasks

1. First use: run the `setup` skill (`/starfield-modding:setup`). It finds the game, saves and mod manager, shows them to the user, and with the user's OK writes the settings file (section 6).
2. Name the sf-papyrus-ref folder for the MCP server: set the plugin option `papyrus_ref`, `papyrus_ref` in the settings file, or the environment variable `SF_PAPYRUS_REF`, to the folder holding `sf_papyrus_ref.py`. To set the option without a dialog, pipe JSON into `claude plugin configure starfield-modding@starfield-modding --values-stdin`, for example `{"papyrus_ref": "C:\\Tools\\sf-papyrus-ref-0.1.0"}` (it prints `Configuration saved.`); `claude plugin configure starfield-modding@starfield-modding` alone shows which options are set. Restart Claude Code afterward. Then check the folder:

       python -I mcp/papyrus_ref_launcher.py --find

   It prints `found <path> (from <source>)` and the command it would run (exit 0), or `not found` (exit 1).
3. Check a hook by hand: put a hook input in a file and pipe it in. Example input for a refused write:

       {"tool_name":"Write","tool_input":{"file_path":"C:/Program Files (x86)/Steam/steamapps/common/Starfield/Data/MyMod.esm","content":"x"}}

   Then run `python -I hooks/guard_game.py < input.json`. It prints a `starfield-modding guard: refused ...` line on stderr and exits 2.
4. Guard more folders (a Vortex staging folder, an MO2 `overwrite` folder): add them to `extra_guarded` in the settings file, or to `SFMOD_EXTRA_GUARDED` separated by `;`.
5. Turn the plugin off for a while: `/plugin`, then disable starfield-modding.

## 6. Inputs

1. Settings, first found wins per key: environment variables `SFMOD_GAME_DIR`, `SFMOD_SAVES_DIR`, `SFMOD_EXTRA_GUARDED`, `SF_PAPYRUS_REF`; then the plugin options (`game_dir`, `saves_dir`, `papyrus_ref`, given to hooks as `CLAUDE_PLUGIN_OPTION_<KEY>`, and `papyrus_ref` to the MCP server through `.mcp.json`); then the project's `.claude/starfield-modding.json`; then the user's `%APPDATA%\starfield-modding\starfield-modding.json` (Windows) or `~/.config/starfield-modding/starfield-modding.json`.
2. Settings file keys: `game_dir`, `saves_dir`, `extra_guarded` (list), `papyrus_ref`, `mod_manager` (`{"kind": "mo2" | "vortex" | "none", "path": ...}`). The README's "Settings" section has an example.
3. Without settings, the guard still covers every Steam library, Game Pass drive, OneDrive Documents and Proton prefix, because it matches the folders by shape.
4. The hooks read Claude Code's hook JSON on stdin. The launcher speaks MCP over stdin and stdout.

## 7. Outputs, exit codes and logs

1. `guard_game.py` and `guard_game_code.py`: exit 0 lets the call go on to the normal permission rules; exit 2 refuses it, with the reason on stderr starting `starfield-modding guard:`. `guard_game_code.py` may instead exit 0 with `permissionDecision: "ask"` on stdout, when a file looks like decompiler output, so the user decides.
2. A hook input the guard can't read is refused (fails closed), and the message names the issue tracker.
3. `papyrus_ref_launcher.py --find`: exit 0 found, 1 not found. In normal use it passes the tool's exit code back.
4. `selftest.py`: exit 0 all passed, 1 a test or the validation failed, 2 Claude Code not found.
5. Logs: hook and launcher messages go to stderr, which Claude Code shows; `claude --debug` shows every hook run. `papyrus_ref_launcher.py --log <file>` also writes the launcher's messages to a file. `selftest.py --verbose` prints each test's name.

## 8. Limits

1. The plugin never changes the game's files, saves or load order, never uploads anything, and makes no network connections of its own. Uploads to Nexus Mods and Bethesda Creations are for the user.
2. The shell guard reads the command's text, so a path built at run time (a variable set in one part and used in the next, a script file the command runs) isn't seen. The file-tool check has no such gap.
3. The game-code guard checks official script names only when sf-papyrus-ref is installed; without it, it checks `.psc` files under `Scripts/Source/Base` and says the check was weaker. The decompiler test is a guess, so it asks instead of refusing.
4. The skills name the commands for the common case. For a tool's other options, read that tool's own `AGENTS.md`.
5. Don't disable the hooks to get a task done. If a hook refuses something it should allow, tell the user and suggest an issue at https://github.com/taosecurity/starfield-modding/issues.
