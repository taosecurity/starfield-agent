# starfield-agent: design

This is the design of `starfield-agent`, a Claude Code plugin and plugin marketplace for Starfield mod authors. It gives an agent the working habits we use for our own mods, as skills it can load and hooks it cannot ignore, and it points each skill at the free public tools that do the real checks.

- Status: design, written 2026-11-20. Built so far (2026-11-20): the manifests, all twelve skills, both hooks, the MCP launcher, 103 tests and `selftest.py`, and the README, AGENTS.md, LICENSE and CHANGELOG, and the clean install test (`NOTES.md`), and both reviews with their fixes (`NOTES.md`, "Reviews"). Version 0.1.0 was released on 2026-11-20.
- Target: version 0.1.0, MIT license. Renamed from starfield-modding to starfield-agent in 0.2.0 (2026-11-21); repo `taosecurity/starfield-agent`. The settings files fall back to the old `starfield-modding.json` names (section 6).
- Checked against: Claude Code 2.1.330 and the official docs at code.claude.com (plugins, plugins-reference, plugin-marketplaces, marketplace-reference, skills, hooks, mcp), read 2026-11-20.

## 1. What a modder gets

After two commands, a modder using Claude Code has:

- twelve skills for the jobs a Starfield mod repeats: set up, start a mod, build it, rebuild someone else's mod, evaluate a mod, write a test plan, review test logs, check a release, handle a game update, the logging rules, the never-share-game-code rules, and a wrap-up;
- a guard hook that stops the agent from writing into the game's `Data` folder, the saves folder or the game's `Plugins.txt`;
- a guard hook that stops the agent from committing or releasing Bethesda's files (game plugins and archives, executables, official script sources, decompiler and Ghidra output);
- the `sf-papyrus-ref` MCP server, so the agent looks Papyrus functions up instead of recalling them.

Install, as the README will show it:

```
claude plugin marketplace add taosecurity/starfield-agent
claude plugin install starfield-agent@starfield-agent
```

Inside a session the same is `/plugin marketplace add taosecurity/starfield-agent`, then `/plugin install starfield-agent@starfield-agent`. Skills are then called as `/starfield-agent:<skill>`, and the agent also loads them by itself when a task matches.

## 2. Folder layout

The repo root is both the marketplace and the plugin (marketplace entry `"source": "./"`), the same shape Universal Modder and BGS Modding Superpowers use.

```
starfield-agent/
  .claude-plugin/
    plugin.json            name, version, description, author, homepage, repository, license, keywords
    marketplace.json       name "starfield-agent", owner, one plugin entry with source "./"
  skills/
    setup/SKILL.md
    new-mod/SKILL.md
    build-mod/SKILL.md
    rebuild-mod/SKILL.md
    evaluate-mod/SKILL.md
    test-plan/SKILL.md
    log-review/SKILL.md
    release-check/SKILL.md
    patch-day/SKILL.md
    logging-rules/SKILL.md
    game-code-rules/SKILL.md
    wrap-up/SKILL.md
  hooks/
    hooks.json             the two PreToolUse guards
    guard_game.py          Data, saves and Plugins.txt guard
    guard_game_code.py     game-code guard for git and gh
    sfmod_config.py        shared: reads the path settings (section 6)
  mcp/
    papyrus_ref_launcher.py   starts sf-papyrus-ref, or a help-only stub when it is missing
  .mcp.json                registers the launcher
  tests/
    test_guard_game.py
    test_guard_game_code.py
    test_launcher.py
    test_skills.py         frontmatter, descriptions, tool names and versions, private-text scan
  selftest.py              runs everything above plus `claude plugin validate .`
  README.md  AGENTS.md  CHANGELOG.md  LICENSE  NOTES.md  DESIGN.md
```

Hooks and the launcher are Python 3 with the standard library only, because every Python-based tool the skills call needs Python anyway. Hook commands use the shell form `python -I "${CLAUDE_PLUGIN_ROOT}/hooks/<file>.py"`.

## 3. Skills

Each skill is one `SKILL.md` with plain numbered steps. Descriptions stay short (under 400 characters), because every skill description is loaded into every session. The skills never embed a tool's full option list: they name the command for the common case and tell the agent to read that tool's `AGENTS.md` for the rest, so a tool release does not make a skill wrong.

Tool versions below are the current GitHub releases, checked 2026-11-20.

| Skill | Use it when | What it does | Tools it calls | Comes from |
|---|---|---|---|---|
| `setup` | First use, or a tool seems missing | Finds the game (Steam, Game Pass), the saves folder and the mod manager (MO2, Vortex); writes the path settings; reports which tools are installed and their versions, with the install command for each missing one | each tool's `--version` or `doctor` | new |
| `new-mod` | "Start a new mod" | Picks the mod name, plugin name and script prefix (naming rules below), makes the project folder, git, a `NOTES.md`, a `CLAUDE.md` with the mod rules, and a builder from the template | sf-mod-build 0.1.1 (`new`, `doctor`), BuildKit 0.4.2 | our build skill and mod rules |
| `build-mod` | "Build", "bump", "package" | Compiles Papyrus with `-optimize` and never `-release`; builds the plugin; checks it; packs the archive and the zip (one plugin per zip, no `.psc` sources in it); records the version | sf-mod-build 0.1.1 (`build`), sf-mod-check 0.9.0 (`check`) | our build skill |
| `rebuild-mod` | Remaking or fixing another author's mod | Permission first, written down; reads the original read-only; matches vanilla and sibling behavior with proper code, not the original's quirks; credits the author; then the build-mod steps | sf-pex-tools 0.1.0 (`compare`), sf-mod-check 0.9.0, BuildKit 0.4.2 | our rebuild rules |
| `evaluate-mod` | "What does this mod do?", "what changed in this update?" | A first evaluation (records, scripts, overlap with the user's mods, permissions) or a compare of two versions (files by hash, scripts by `.pex` compare, plugins record by record), then whether it affects the user's own mods and load order | sf-mod-check 0.9.0 (`check`, `conflict`), sf-pex-tools 0.1.0, sf-load-order 0.1.1, sf-cut-check 0.1.9 (optional) | our evaluation shortcut |
| `test-plan` | Before a test session | Writes a test plan for a new character, with a log rule for each check the log can prove | sf-test-plan 0.2.0 | our test plan habit |
| `log-review` | After a test session | Reads a log-collector package: Papyrus log rules first, then the plan's log checks, crash logs and a save check; drafts a result per mod. NOT SEEN means not tested, not failed | sf-log-collector 2.0.1, papyrus-log-check 0.3.2, sf-test-plan 0.2.0, sf-save-health 0.7.1, sf-save-reader 0.1.3 | our log review skill |
| `release-check` | Before an upload | Runs the release profile, checks permission and credits on record, the README's Papyrus logging section, naming, one plugin per zip, and for Creations the console rules; lists the archive contents. The user does the upload | sf-mod-check 0.9.0 (`release`), sf-papyrus-ref 0.1.0 (`check --creations`) | our release rules |
| `patch-day` | After a game update | Checks DLL mods against the new game version and every project for drift, and writes one summary | sf-patch-day 0.1.3, sf-load-order 0.1.1 | our patch-day routine |
| `logging-rules` | Writing or reviewing Papyrus | `Debug.Trace` with the mod's prefix in every script; a "Show Debug Messages (PC only)" option, off by default, in the mod's own Gameplay Options group; text the player must see as a Message record with `Show()`, since `Debug` does nothing on consoles; the README says how to turn on Papyrus logging | sf-papyrus-ref 0.1.0 (lookups) | our logging rule |
| `game-code-rules` | Any commit, release, issue, post or chat that carries code | What may be shared (format facts, symbol names, your own code) and what never may (game executables and files, official `.psc`, decompiled code, Ghidra projects); what the hook enforces and what it can't | none | our never-share-game-code rule |
| `wrap-up` | End of a work session | Updates the project's `NOTES.md` (what changed, why, the next step), commits finished and checked work with a clear message, and says what was committed; never commits saves, game files or build output | git | our wrap-up habit |

Rules that several skills share (they live in `logging-rules`, `new-mod` and `build-mod`, written once and linked):

- Plugin names are `<ModName>.esm`, with no spaces. A plugin name must never end in an official plugin's name (`-ShatteredSpace.esm`, `-Constellation.esm`, `-Starfield`, `-OldMars`, `-SFBGS…`) or start with `BlueprintShips-`, because the game drops such names from `Plugins.txt`. Use an `Addon` suffix instead.
- Prefer conflict-free designs: no vanilla record edits unless the design needs them; inject with scripts and use the mod's own records.
- Test with a new character.
- Effect entries need EFIF and MUID, or they never apply (BuildKit adds them).
- Mutagen-based builders write ONAM like the Creation Kit (BuildKit does).
- Prove a bug in someone else's mod before reporting it: current version, own setup ruled out, code shown to run, evidence written down.

## 4. Hooks

### 4.1 guard_game (PreToolUse, matcher `Edit|Write|NotebookEdit|Bash|PowerShell`)

Chapter 15 of our modding guide shows a blunt version that refuses any command naming the folders. That version also refuses `sf-mod-check check --data "<game>\Data"`, which every skill needs, so the plugin's guard is narrower but still fails closed:

1. File tools (`Edit`, `Write`, `NotebookEdit`): refuse when `file_path` (always absolute) is inside a guarded folder or is a guarded file. Paths are compared after normalizing slashes, case and `..`, and after resolving links where the file exists.
2. Shell tools (`Bash`, `PowerShell`): when the command names a guarded path, allow it only if every part of it (split on `;`, `&&`, `||`, `|`, newlines) starts with a known read-only command (`ls`, `dir`, `Get-ChildItem`, `cat`, `type`, `Get-Content`, `Test-Path`, `file`, `sha256sum`, `Get-FileHash`, and the read-only modes of the PMT tools such as `sf-mod-check check|conflict`, `sf-save-health check`, `sf-cut-check find|scan --out <elsewhere>`, `sf-load-order`), and no part has output redirection (`>`, `>>`, `Out-File`, `Set-Content`, `Tee-Object`). Anything else that names a guarded path is refused. The list is in one table at the top of the script, so a user can read it.
3. Guarded by default: the game's `Data` folder (Steam `steamapps\common\Starfield\Data` in any library, Game Pass `XboxGames\Starfield\Content\Data`), the saves folder (`Documents\My Games\Starfield\Saves`, the OneDrive copy of Documents, and the Game Pass save container under `%LOCALAPPDATA%\Packages\BethesdaSoftworks.ProjectGold_*`), and `%LOCALAPPDATA%\Starfield\Plugins.txt`. Settings can add folders (a Vortex staging folder, an MO2 `overwrite` folder) or point at a moved install.
4. The message says what was refused and why, and asks the agent to let the user copy the file in or use the mod manager.
5. If Python is missing the hook can't run. The hook entry sets `"onFailure": "block"` (Claude Code 2.1.295 and later) so it fails closed, and the `setup` skill checks Python first.

As built in step 3 (`hooks/guard_game.py`, 41 tests in `tests/test_guard_game.py`):

- A command "names" a guarded path when any path-like word (also after `--data=` or `-Path:`) normalizes into one (environment variables such as `$env:LOCALAPPDATA` expanded, Git Bash `/c/...` and WSL `/mnt/c/...` read as `C:\...`, `..` folded, links resolved where the path exists), or when the whole command, with quotes and `\ ` escapes removed, contains a guarded shape. A command whose working folder is inside a guarded folder counts as naming it, and there only the plain listing and reading commands pass, since a tool's default output would land in that folder.
- A command that names a guarded path is also refused when it holds `$(...)`, backticks or `<(...)`, which the guard can't read, or a PowerShell cmdlet that changes files (`Out-File`, `Set-Content`, `Copy-Item`, `Remove-Item` and the like) anywhere in it. `2>&1`, `2>/dev/null` and `>$null` aren't redirections into a file.
- The read-only table has two parts: plain commands (any arguments, `sort -o` excepted) and the PMT tools with their read-only modes. A tool's output options (`--out`, `--log`, `--state` and the like) must not point into a guarded folder.
- Guarded by shape, so any Steam library, Game Pass drive, OneDrive Documents or Proton prefix is covered without detection: `.../steamapps/common/Starfield/Data`, `.../XboxGames/Starfield/Content/Data`, `.../My Games/Starfield/Saves`, `.../Packages/BethesdaSoftworks.ProjectGold_*`, and `AppData/Local/Starfield/Plugins.txt` and `ContentCatalog.txt` (the second added in step 3: the game and the mod managers own it too). The settings add `game_dir\Data`, `saves_dir` and each `extra_guarded` folder.
- A hook input it can't read is refused (fail closed), and the message says how to report it and how to turn the plugin off meanwhile.
- Known limits: a shell guard reads text, so a path built at run time (a variable assigned in one part and used in the next, a script file the command runs) isn't seen. The skills say this, and the file-tool check has no such gap.
- Changed after the 0.1.0 code review (NOTES.md, "Reviews"): every word is now resolved against its part's working folder, and the guard follows `cd`, `Set-Location`, `pushd` and `chdir`, so `rm -rf Data` from the game folder and `cd Data && del x` are refused; wildcard words are expanded with `glob` and every match checked; a folder that holds a guarded folder (such as the game folder itself) counts as naming it, so writes to it are refused while reads pass; the rule that only plain commands run inside a guarded working folder now applies whether or not the command also names a guarded path; `uniq` and `ba2-extract extract` left the read-only list; and a part that names a guarded folder and holds PowerShell code (`{ }`, `( )` expressions, `::`, `.Method(`) outside quotes is refused.

### 4.2 guard_game_code (PreToolUse, matcher `Bash|PowerShell`, only for `git add|commit|push`, `gh release create|upload`, `gh gist create`)

1. For `git commit` and `git push`, it lists the files that would go up (`git diff --cached --name-only`, or `git diff --name-only @{u}..` for a push) in the command's repo. For `git add` and `gh release`, it reads the named paths.
2. It refuses when any of them is: an official plugin or archive by name (`Starfield.esm`, `Constellation.esm`, `OldMars.esm`, `ShatteredSpace.esm`, `BlueprintShips-Starfield.esm`, `SFBGS*.esm`, `Starfield - *.ba2` and the DLC archives); the game's executable or its DLLs (`Starfield.exe`, `CreationKit.exe`); a Ghidra project (`*.gpr`, `*.rep`); a save (`*.sfs`); or a `.psc` whose script name is an official script. Official script names come from `sf-papyrus-ref script <name>` when that tool is installed (names are symbol data; the tool ships no Bethesda code). Without it, the hook refuses `.psc` files under a folder named `Scripts\Source\Base` or `Source\Scripts` copied from the Creation Kit, and says that the check is weaker.
3. It also refuses a file whose first lines carry a decompiler banner (Champollion and Ghidra's export headers). This is a heuristic, and the `game-code-rules` skill says so.
4. It never runs the command itself and never changes the repo.

Whether a generic game-code guard is good enough is settled in step 3 with tests. If the decompiler and `.psc` checks give false alarms on a modder's own scripts, they drop to warnings (exit 0 with a message) and only the by-name checks refuse.

Settled in step 3 (`hooks/guard_game_code.py`, 24 tests in `tests/test_guard_game_code.py`):

- Refused (exit 2): official plugins and archives by name, `Starfield.exe`, `CreationKit.exe`, the Creation Kit's `ContentResources.zip` (its zip of official script sources), Ghidra projects (`.gpr`, anything in a `.rep` folder), IDA databases (`.i64`, `.idb`), saves (`.sfs`), `.psc` files under `Scripts/Source/Base`, and `.psc` files whose name sf-papyrus-ref's `script <name>` finds (exit 0). The game's other DLLs are not checked by name, since their names change between versions and many are shared with other games.
- Asked (exit 0 with `permissionDecision: "ask"`, so the user decides): a text file (`.psc`, `.c`, `.cpp`, `.h`, `.txt` and the like) whose first 4 KB look like decompiler output (a Champollion or Hex-Rays banner, a "decompiled by" comment, Ghidra's `/* WARNING: ...` lines, or two or more `FUN_`/`DAT_` names with `undefined` types). This is the warning form the paragraph above allows: the banner test is a guess.
- What it lists: `git add` through `git add --dry-run` with the same arguments; `git commit` from the index (`git diff --cached`), plus tracked changes for `-a` and named paths; `git push` from every commit the push would send (`git log <revs> --not --remotes`), so a file added and removed again in later commits is still caught; `gh release create|upload` and `gh gist create` from the named files, reading the members of a `.zip`. It follows `cd`, `Set-Location` and `git -C`.
- False-alarm check (step 3): the checks ran over 11,395 git-tracked `.psc`, `.c`, `.cpp`, `.h` and `.txt` files in 228 local repos of our own and of other authors we follow, with sf-papyrus-ref installed. Our own scripts raised nothing. Seventeen refusals were all edited copies of official scripts in other authors' patch repos (they keep the official name so they replace the game's script), which the rule says never to share. The one "ask" was decompiler pseudocode quoted in a C++ comment. So the by-name checks stay refusals, and only the content test asks.
- Without sf-papyrus-ref, `.psc` files are checked by the `Scripts/Source/Base` folder only, and the message says the check was weaker.
- Changed after the 0.1.0 reviews (NOTES.md, "Reviews"): when the files can't be listed (a git error) it now asks instead of passing; a first commit with pathspecs is listed with `git ls-files`; `git push <remote> tag <name>` is read as the tag; push revisions go after `--end-of-options` and remote tips are excluded as `^<sha>`, so a refspec such as `+--output=<file>` can't turn into a `git log` option that writes a file; zips are opened on commit (staged and working copy) and on push (from the commit), not only on `git add` and `gh`; `gh release` and `gh gist` file arguments with wildcards are expanded, and the tag is no longer taken for a file; and sf-papyrus-ref is found with `safe_which` and never from the project's settings file.

## 5. MCP: sf-papyrus-ref

`sf-papyrus-ref` is a separate download (a folder holding `sf_papyrus_ref.py`), so the plugin can't name its path. `.mcp.json` registers a small launcher:

```json
{
  "mcpServers": {
    "papyrus-ref": {
      "command": "python",
      "args": ["-I", "${CLAUDE_PLUGIN_ROOT}/mcp/papyrus_ref_launcher.py"]
    }
  }
}
```

1. The launcher finds the tool from the `papyrus_ref` setting (section 6), then the `SF_PAPYRUS_REF` environment variable (the folder), then `sf_papyrus_ref.py` on `PATH`.
2. Found: it runs `python -I <folder>/sf_papyrus_ref.py mcp --quiet` (the command in the tool's `AGENTS.md`) and passes stdin and stdout through. The four read-only tools appear as `mcp__plugin_starfield-agent_papyrus-ref__papyrus_lookup` and so on.
3. Not found: it serves a minimal MCP server with one tool, `papyrus_setup_help`, which returns the download link and the setting to fill. That way a modder without the tool sees no failed server at every start, and the agent learns how to fix it.
4. The launcher makes no network connections.

As built (step 5 of the relay, 2026-11-20):

- The launcher reads the `papyrus_ref` setting through `hooks/sfmod_config.py`'s `load_settings`, so it uses the same order as the hooks: `SF_PAPYRUS_REF`, the plugin option `CLAUDE_PLUGIN_OPTION_PAPYRUS_REF`, then the user file (the project file is not trusted for this key; section 6). A `--papyrus-ref <folder>` argument comes first, and PATH (`sf_papyrus_ref.py`, then the `sf-papyrus-ref` command) comes last. Empty values and unsubstituted `${...}` placeholders are ignored.
- The clean install test (relay step 7, 2026-11-20, Claude Code 2.1.330) showed that Claude Code does not export `CLAUDE_PLUGIN_OPTION_PAPYRUS_REF` to MCP server processes on its own: with the option set, the launcher still served the help-only stub. So `.mcp.json` passes it explicitly, as `"env": {"CLAUDE_PLUGIN_OPTION_PAPYRUS_REF": "${user_config.papyrus_ref}"}`. Tested both ways: with the option set, the real server's four tools appear; with it unset, the server is not skipped and the stub still appears (the launcher ignores the empty or unsubstituted value). Details in `NOTES.md`.
- `--find` prints what the launcher would start and exits (0 found, 1 not found); `--log <file>` copies its messages, which otherwise go to stderr, to a file.
- `tests/test_launcher.py` (12 tests): the stub's replies, bad lines and unknown methods, each way of finding the tool with a fake echoing `sf_papyrus_ref.py`, the exit code passed back, and one real run against an installed sf-papyrus-ref (set `SFMOD_TEST_PAPYRUS_REF` or `SF_PAPYRUS_REF`; skipped otherwise).

Future idea, out of scope for 0.1.0 (confirmed at step 5): `sf-plugin-mcp`, a read-only MCP server built on our own plugin readers that answers "what is this FormID", "what points at it" and "who wins it in this load order" with gate-grade data.

## 6. Paths and settings

Settings are read in this order, the first one found wins for each key:

1. Environment variables: `SFMOD_GAME_DIR`, `SFMOD_SAVES_DIR`, `SFMOD_EXTRA_GUARDED` (paths separated by `;`), `SF_PAPYRUS_REF`.
2. The project's `.claude/starfield-agent.json`.
3. The user's `starfield-agent.json` in `%APPDATA%\starfield-agent\` on Windows or `~/.config/starfield-agent/` elsewhere.
4. Detected defaults: every Steam library listed in `steamapps\libraryfolders.vdf`, Game Pass `<drive>:\XboxGames\Starfield\Content`, Documents (with the OneDrive move read from the registry's Known Folders), and the mod manager found by the `setup` skill.

The `setup` skill writes file 3 after showing the user what it found. Keys in files 2 and 3 (fixed in step 2a): `game_dir` (the folder holding `Starfield.exe`), `saves_dir`, `extra_guarded` (a list of folders), `papyrus_ref` (the folder holding `sf_papyrus_ref.py`) and `mod_manager` (`{"kind": "mo2" | "vortex" | "none", "path": ...}`). Mod managers:

- MO2: the agent builds into the project folder, and MO2's mod folder for the mod is set as the output only if the user asks. MO2's virtual `Data` means the real `Data` stays clean; the guard still covers it.
- Vortex: the user drops the zip on Vortex. Vortex's staging folder can be added to the guarded list.

Plugin `userConfig` (a manifest field the reference lists) may replace file 3. Step 3 tests whether hooks can read its values; if they can, it is used, and the file stays as the fallback.

Answer (step 3, from the plugins reference read 2026-11-20): yes. Claude Code exports every option to hook processes as `CLAUDE_PLUGIN_OPTION_<KEY>` (key upper-cased), and substitutes `${user_config.KEY}` in MCP server configs and in exec-form hook arguments, but not in shell-form hook commands. So `plugin.json` declares three optional `directory` options, `game_dir`, `saves_dir` and `papyrus_ref`, which Claude Code offers when the plugin is enabled, and `sfmod_config.py` reads `CLAUDE_PLUGIN_OPTION_GAME_DIR`, `..._SAVES_DIR`, `..._PAPYRUS_REF` and `..._EXTRA_GUARDED` right after the `SFMOD_*` variables (an empty value counts as unset). `extra_guarded` and `mod_manager` stay in the settings files, which remain the fallback. `claude plugin validate .` accepts the options. The clean install test (step 6) must confirm that a value set in the dialog reaches the hook.

Changed after the 0.1.0 reviews (see NOTES.md, "Reviews"):

- The project file is never read for `papyrus_ref`: that key names a program the hooks and the MCP server run, and a downloaded project could ship its own settings file and script. The guard notes that it ignored it.
- The folder keys (`game_dir`, `saves_dir`, `extra_guarded`) are no longer "first found wins": every folder named in any layer is guarded, so a project file can add folders but never remove one the user guards.
- Unfilled `${...}` placeholders count as unset in every layer, so an unset plugin option doesn't hide the files below it.
- PATH lookups (`sfmod_config.safe_which`) skip the current folder, relative PATH entries and the project folder, because Windows' `shutil.which` looks in the current folder first.
- `SFMOD_HOOK_LOG` names a troubleshooting log both guards append to.

## 7. What stays out, and why

- Our dashboard, publishing queue, test-package folders, log handoff folders, memory notes and session relays: they serve our own setup and would mean nothing to another modder.
- Uploads to Nexus Mods and Bethesda Creations: the user does them, signed in with their own account.
- Reverse-engineering skills (Ghidra, decompiling): they handle game code, which the plugin exists to keep out of public places.
- Our Creation Kit docs skill: it is built on a private copy of the wiki.
- Third-party tools we use privately (SFSearch, xEdit scripts): skills may mention xEdit as the user's choice, but the plugin calls only our public tools.
- House rules such as our version naming for dated patches, our test account names and our folder names.
- A rules file that loads into every session: the plugin adds skills and hooks only, and the `new-mod` skill writes a project `CLAUDE.md` that the user can edit.

## 8. Test plan

Every skill and hook gets a test, added in the step that adds it.

1. `selftest.py` runs, and must pass before each commit:
   - `claude plugin validate .` (and `--strict` once warnings are cleared);
   - `tests/test_skills.py`: each `SKILL.md` has frontmatter with `name` equal to its folder and a description under 400 characters; every tool and version a skill names matches a table in `tests/tool_versions.json`; no private text (our folder names, our account names, our handoff folders);
   - `tests/test_guard_game.py`: JSON on stdin for each case, exit 2 or 0 expected: writes into Steam and Game Pass `Data`, saves, OneDrive saves and `Plugins.txt` refused; `sf-mod-check check --data <Data>` and `dir <Data>` allowed; `dir <Data> > out.txt`, `copy x <Data>` and `ls <Data>; rm <Data>\x.esm` refused; mixed slashes, case and `..` handled; a settings file adds a folder;
   - `tests/test_guard_game_code.py`: a temporary git repo with a staged `Starfield.esm`, an official `.psc` name, a `.gpr`, a decompiler banner, and the modder's own `.psc`; the first four refused, the last allowed;
   - `tests/test_launcher.py`: the stub answers `initialize` and `tools/list` with `papyrus_setup_help`; with a fake `sf_papyrus_ref.py` that echoes, the launcher passes messages through.
2. Clean install test (step 6): a fresh `CLAUDE_CONFIG_DIR` in an empty scratch folder; `claude plugin marketplace add <local repo>`, `claude plugin install starfield-agent@starfield-agent`, `claude plugin list`, then a headless `claude -p` asked to list its skills, and a hook check (a refused write into a fake `Data` folder named by the settings). Results go in `NOTES.md`.
3. Haiku agent test (step 8): one agent given only `AGENTS.md` and a clean copy of the repo installs the plugin into a fresh config folder and lists its skills.
4. `readme-check` exits 0 (closest kind: `tool`).

## 9. Similar projects and credit

Searched 2026-11-20 (GitHub, Claude Code plugin directories, skill directories). None is for Starfield.

- [rehan-remade/universal-modder](https://github.com/rehan-remade/universal-modder), MIT, read at `a34eae7`: a general modding plugin. We borrow its shape (the repo root as both marketplace and plugin, `"source": "./"`). We use none of its code or text.
- [BB-84C/bgs-modding-superpowers](https://github.com/BB-84C/bgs-modding-superpowers), MIT, read at `74d705a`: a Bethesda modpack-curation plugin for Skyrim and Fallout (MO2, xEdit, Papyrus). Same root-plugin shape; we use none of its code or text.
- Spooky's Automod Toolkit Papyrus skill and skyrim-opencode-toolkit: Skyrim only, not used.

The README's Credits section names the first two for the layout. A cross-link or upstream contribution is for later, and only with the user's OK.

## 10. Build order (the relay's plan)

1. This design.
2. The skills (may take two steps: setup, new-mod, build-mod, rebuild-mod, evaluate-mod, test-plan first; then log-review, release-check, patch-day, logging-rules, game-code-rules, wrap-up), each with its test.
3. The two hooks and `sfmod_config.py`, with tests; test `userConfig`.
4. The MCP launcher and `.mcp.json`, with tests.
5. README, AGENTS.md, LICENSE, CHANGELOG 0.1.0, manifests; `readme-check` exits 0.
6. Clean install test.
7. `/code-review` (medium) and `/security-review`; fix and retest.
8. Haiku agent test.
9. Create the repo, push, tag and release 0.1.0.
