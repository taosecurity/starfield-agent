# starfield-modding: test notes

## Clean install test (2026-11-20)

Claude Code 2.1.330 on Windows 11, Python 3.13. The plugin at commit b953cd2 (0.1.0, unreleased). In the output below, `<test>` is an empty scratch folder made for this test, `<clone>` is `<test>\clone-1` (a fresh `git clone` of the repo), `<config>` is `<test>\config-1` (an empty folder), and `<ref>` is a folder holding sf-papyrus-ref 0.1.0.

### Summary

- Adding the marketplace from a local clone, installing the plugin and listing it all work in an empty config folder (`CLAUDE_CONFIG_DIR`).
- A Claude Code session sees all twelve skills and the `papyrus-ref` MCP server.
- The `game_dir` plugin option reaches the guard hook: a write into `<fake game>\Data` is refused because of the option, and the same write goes through without it.
- Plugin options can be set without the dialog: `claude plugin install ... --config KEY=VALUE`, or JSON piped into `claude plugin configure <plugin> --values-stdin`. They are stored in the config folder's `settings.json` under `pluginConfigs`.
- The `papyrus_ref` option does **not** reach the MCP server by itself. Passing it in `.mcp.json` as `"env": {"CLAUDE_PLUGIN_OPTION_PAPYRUS_REF": "${user_config.papyrus_ref}"}` works, and with the option unset the server still starts (as the help stub). `.mcp.json` now does that.
- Docs fixed: README (plugin options reach the MCP server too; how to set them from the command line; the plugin's cache folder), AGENTS.md (the same, and the exact `claude plugin list` status text), DESIGN.md section 5.

### 1. Install into an empty config folder

```
> $env:CLAUDE_CONFIG_DIR = "<config>"
> claude plugin marketplace add <clone>
Adding marketplace…✔ Successfully added marketplace: starfield-modding (declared in user settings)

> claude plugin install starfield-modding@starfield-modding
Installing plugin "starfield-modding@starfield-modding"...✔ Successfully installed plugin: starfield-modding@starfield-modding (scope: user)
3 userConfig options not yet set — run /plugin configure starfield-modding@starfield-modding in Claude Code, or pass --config KEY=VALUE.

> claude plugin list
Installed plugins:

  ❯ starfield-modding@starfield-modding
    Version: 0.1.0
    Read from: <clone>
    Scope: user
    Status: ✔ enabled
```

All three exit 0. `<config>\plugins\installed_plugins.json` gives the install path as `<config>\plugins\cache\starfield-modding\starfield-modding\0.1.0` (a copy of the repo at the installed commit). So the README's "under `~/.claude/plugins`" is right for the default config folder; it now names the full cache path.

### 2. Setting a plugin option from the command line

```
> claude plugin configure starfield-modding@starfield-modding
Options for starfield-modding (starfield-modding@starfield-modding):
  ❯ game_dir — Starfield game folder (optional) (optional, not set)
  ❯ saves_dir — Starfield saves folder (optional) (optional, not set)
  ❯ papyrus_ref — sf-papyrus-ref folder (optional) (optional, not set)

> '{"game_dir":"<test>\\fakegame-1"}' | claude plugin configure starfield-modding@starfield-modding --values-stdin
Configuration saved. Restart Claude Code to apply it.
```

`<config>\settings.json` then holds `"pluginConfigs": {"starfield-modding@starfield-modding": {"options": {"game_dir": "<test>\\fakegame-1"}}}`.

### 3. A Claude Code session

The empty config folder has no login (`claude -p` there answers `Not logged in · Please run /login`), and copying a login into a scratch folder is not safe. So the session checks ran with a normal, logged-in config and the clone loaded for that session only (`--plugin-dir <clone>`, which names the plugin `starfield-modding@inline`). The plugin options went in a `--settings` file with the same `pluginConfigs` shape as above.

Skills and MCP servers (`claude -p "List the skills whose names start with 'starfield-modding:' ..." --plugin-dir <clone>`):

```
starfield-modding:build-mod
starfield-modding:evaluate-mod
starfield-modding:game-code-rules
starfield-modding:log-review
starfield-modding:logging-rules
starfield-modding:new-mod
starfield-modding:patch-day
starfield-modding:rebuild-mod
starfield-modding:release-check
starfield-modding:setup
starfield-modding:test-plan
starfield-modding:wrap-up

Count: 12

- `plugin:starfield-modding:papyrus-ref` (tool name: `mcp__plugin_starfield-modding_papyrus-ref__papyrus_setup_help`)
```

(No sf-papyrus-ref named, so the help stub is right.)

**(a) Does a plugin option reach the guard hook?** Yes. With `game_dir` set to `<test>\fakegame-1` (not a folder the guard knows by its shape), the session was asked to Write `<test>\fakegame-1\Data\Probe.esm`:

```
PreToolUse:Write hook error: [python -I "<clone>/hooks/guard_game.py"]: starfield-modding guard: refused to change <test>\fakegame-1\Data\Probe.esm, because it is in the game's Data folder (game_dir setting).
Copy the file in yourself or install it with your mod manager; the agent only reads these folders. To guard more folders or point at a moved install, see the starfield-modding README, "Settings".

This hook comes from the starfield-modding@inline plugin.
```

The file was not made. The control run (same command, no option) wrote the file ("File created successfully"); it was deleted afterward. No `SFMOD_*` variable or settings file was present, so the option is what refused it.

**(b) Does the `papyrus_ref` option reach the MCP server?** Not by itself. With `papyrus_ref` set to `<ref>` in the same settings file, the server still served only `papyrus_setup_help`, so `CLAUDE_PLUGIN_OPTION_PAPYRUS_REF` was not in the server's environment. A copy of the clone with this in `.mcp.json`:

```json
"env": {"CLAUDE_PLUGIN_OPTION_PAPYRUS_REF": "${user_config.papyrus_ref}"}
```

gave, with the option set:

```
- mcp__plugin_starfield-modding_papyrus-ref__papyrus_check
- mcp__plugin_starfield-modding_papyrus-ref__papyrus_list_flag
- mcp__plugin_starfield-modding_papyrus-ref__papyrus_lookup
- mcp__plugin_starfield-modding_papyrus-ref__papyrus_script
```

and, with the option unset, the server still started with `papyrus_setup_help` (it was not skipped for missing configuration). The repo's `.mcp.json` now has that line, and `tests/test_launcher.py` checks it.

### 4. AGENTS.md sections 4 and 5, run in the clone

```
> python -I selftest.py
...
selftest: claude plugin validate OK
RESULT: OK                                  (exit 0)

> python -I mcp/papyrus_ref_launcher.py --find
papyrus-ref launcher: sf_papyrus_ref.py is not on PATH
not found                                   (exit 1)

> $env:SF_PAPYRUS_REF = "<ref>"
> python -I mcp/papyrus_ref_launcher.py --find
papyrus-ref launcher: found <ref>\sf_papyrus_ref.py (from environment variable SF_PAPYRUS_REF)
<python> -I <ref>\sf_papyrus_ref.py mcp --quiet      (exit 0)

> python -I hooks/guard_game.py < input.json        (the Write example in AGENTS.md section 5)
starfield-modding guard: refused to change C:/Program Files (x86)/Steam/steamapps/common/Starfield/Data/MyMod.esm, because it is in the game's Data folder (Steam).
Copy the file in yourself or install it with your mod manager; ...      (exit 2)
```

After the `.mcp.json` change, `python -I -X utf8 selftest.py` in the repo (with sf-papyrus-ref named for the real-run test) ran 83 tests, OK, and `claude plugin validate` passed.

### Not tested here

- Installing from GitHub (`claude plugin marketplace add taosecurity/starfield-modding`): the repo isn't published yet.
- The `/plugin configure` dialog itself (interactive); the command-line path stores the same `pluginConfigs` entry.
- A full session in the empty config folder (no login there); see section 3.

## Reviews (2026-11-20)

Both reviews ran on the whole repo at 08f3809 (0.1.0, unreleased). There is no remote yet, so `/security-review` was given the first commit (3c2d175, which holds only `DESIGN.md` and `.gitignore`) as its base through a temporary `refs/remotes/origin/HEAD`, deleted afterward. Its diff therefore covered every code file. An empty-tree base didn't work, because the review needs a merge base.

### Summary

- `/code-review` (medium) found 10 issues: 9 important and 1 nit. `/security-review` found 3, all confirmed by reading the code. One of them was also found by the code review, so there were 12 separate issues.
- All 12 are fixed. Each fix has a test (20 new tests, 103 in all), and every new test was checked to fail on the old code (the hooks and launcher stashed, the new tests run, 20 failures and errors) and to pass on the new code.
- One finding (Python named `python3` only, on Linux and macOS) is fixed in the docs and the setup skill, not in code. The reason is below.

### Code review findings and fixes

1. **An unset plugin option hid the settings files.** `.mcp.json` passes `${user_config.papyrus_ref}`. When that placeholder wasn't filled in, it won over the user's file. Fix: `sfmod_config.is_unset` treats empty values and `${...}` placeholders as unset in every layer. Tests: `test_user_settings_file_used_when_option_is_a_placeholder` and `test_placeholder_option_does_not_hide_user_file`.
2. **Relative paths and `cd` slipped past the Data guard.** From the game folder, `rm -rf Data` and `cd Data && del x` passed. Fix: every word is now resolved against the working folder of its part, and the guard follows `cd`, `Set-Location`, `pushd` and `chdir`. Tests: `test_relative_data_from_game_root_refused`, `test_cd_into_data_then_delete_refused` and `test_cd_into_data_then_read_allowed`.
3. **Wildcards slipped past the Data guard.** `rm ".../Starfield/Dat*/x.esm"` passed. Fix: wildcard words are expanded with `glob` and every match is checked. A folder that holds a guarded folder (such as the game folder) also counts as naming it, so writes to it are refused and reads still pass. Tests: `test_wildcard_into_data_refused` and `test_parent_of_data_refused_for_writes_only`.
4. **A tool's default output could land in a guarded working folder.** This happened when the command also named a guarded path, for example `sf-load-order --data <Data>` run inside Data. Fix: the working-folder rule now always applies. Test: `test_tool_in_data_cwd_refused_even_when_naming_data`.
5. **Holes in the read-only list.** PowerShell code such as `Where-Object { $_.Delete() }`, `(Get-Item x).Delete()` and `[IO.File]::Delete` went through. So did `uniq in out` and `ba2-extract extract`. Fix: a part that names a guarded folder and holds `{ }`, a `( )` expression, `::` or `.Method(` outside quotes is refused, and `uniq` and `extract` were taken off the list. Tests: `test_script_block_refused` and `test_uniq_and_ba2_extract_no_longer_read_only`.
6. **The game-code guard failed open on git errors.** Fix: when it can't list the files, it now asks (`permissionDecision: "ask"`). A first commit with pathspecs is listed with `git ls-files`, and `git push <remote> tag <name>` is understood. Tests: `test_first_commit_with_pathspec_checked`, `test_push_tag_keyword_checked` and `test_push_option_injection_writes_nothing`.
7. **Zips weren't opened on commit or push.** Fix: zips are now opened on commit (the staged copy and the working copy) and on push (the copy in the commit). Test: `test_tracked_zip_checked_on_commit_and_push`.
8. **`gh release` wildcards weren't expanded, and the tag was taken for a file.** Fix: wildcards are expanded and the arguments are now sliced correctly. Test: `test_release_wildcard_expanded`.
9. **A project settings file could weaken the guards or pick the program they run.** Fix: the folder keys now add up across all layers, so a project can add folders but never remove one, and `papyrus_ref` is never read from the project file. Tests: `test_project_file_cannot_unguard_user_install`, `test_project_settings_cannot_pick_the_program` and `test_project_settings_file_ignored`.
10. **`python` versus `python3` on Linux and macOS (important).** Not changed in code. A fallback such as `python3 ... || python ...` would run the guard twice. On Windows, `python3` can be the Microsoft Store stub, which exits 9009 and would let the call through. The hooks stay on `python`. The README (Troubleshooting) and the setup skill now say to install `python-is-python3` or make a `python` link. `onFailure: block` is documented for Claude Code 2.1.295 and later (DESIGN.md 4.1, item 5).
11. **The hooks had no troubleshooting log (nit).** Fix: when `SFMOD_HOOK_LOG` names a file, both guards append to it the command they read, what they found and what they decided. Test: `test_hook_log`.

### Security review findings and fixes

1. **High: code from a cloned repo could run through a project settings file.** `papyrus_ref` in `.claude/starfield-modding.json` made the game-code guard (on any `.psc` in git add, commit or push) and the MCP launcher (at session start) run `<folder>/sf_papyrus_ref.py`. This happened before any permission prompt. It is the same issue as code review item 9, with the same fix.
2. **High: a planted program in the project folder could run through PATH.** On Windows, `shutil.which` looks in the current folder first. That let a `sf-papyrus-ref.bat` or `sf_papyrus_ref.py` in the repo run with no settings at all. Fix: `sfmod_config.safe_which` skips the current folder, relative PATH entries and the project folder. Both the hook and the launcher use it. Tests: `test_program_planted_in_project_not_found_on_path` and `test_program_in_project_not_taken_from_path`.
3. **Medium: options could be injected into `git log`.** A refspec such as `+--output=<file>` became a `git log` option that writes a file. That happened inside the hook, before the permission prompt. Fix: push revisions now go after `--end-of-options`, and remote tips are excluded as `^<sha>` instead of `--not --remotes`. Test: `test_push_option_injection_writes_nothing` (no file is written, and the user is asked).

### Checks after the fixes

- `python -I -X utf8 selftest.py` with `SFMOD_TEST_PAPYRUS_REF` naming a local sf-papyrus-ref 0.1.0: 103 tests, OK, including the real-server test. `claude plugin validate` passed with only the ICON_MISSING directory note.
- readme-check `--kind tool`, the private-text grep and the removal of `__pycache__`: see the relay log for this step.

## Haiku agent test (2026-11-20)

One test agent (Claude Haiku) got only a fresh clone at 7ee872a, an empty `CLAUDE_CONFIG_DIR` and the task: follow AGENTS.md to run the selftest, add the clone as a local marketplace, install the plugin, run `claude plugin list`, and list the skills. It was not told the answers.

### What it ran and saw

- `python -I selftest.py` (AGENTS.md 4.2): 103 tests, OK (1 skipped, the real sf-papyrus-ref run), `claude plugin validate` OK with the ICON_MISSING note, `RESULT: OK`, exit 0.
- With the empty config: `claude plugin marketplace add <clone>` ("Successfully added marketplace: starfield-modding"), `claude plugin install starfield-modding@starfield-modding` (installed, "3 userConfig options not yet set"), `claude plugin list` (version 0.1.0, `Status: ✔ enabled`). All exit 0.
- Skills: AGENTS.md gave no way to list them. It read the 12 folders under `skills/` and found `claude plugin details starfield-modding@starfield-modding` through `claude plugin --help`: `Skills (12)`, `Hooks (1)  PreToolUse`, `MCP servers (1)  papyrus-ref`. The clone stayed clean (`git status --short` empty).

### What it tripped on, and the fixes (docs only)

1. No command to list the skills. Fixed: AGENTS.md 4.2 now gives `claude plugin details`, with its expected lines, and the `skills/` folders as the fallback; the README install section names it too. Rerun in the empty config: exit 0, the same output.
2. AGENTS.md says two PreToolUse hooks, `plugin details` says `Hooks (1)`. Both are right: `hooks/hooks.json` has two PreToolUse entries, and `details` counts hook events. AGENTS.md 1.3 now says so.
3. Unclear whether the selftest uses the default config. It runs `claude plugin validate .`, which reads only the plugin folder. AGENTS.md 4.3 now says so, and that ICON_MISSING is not a failure. (`-X utf8` is not needed: the selftest sets its own output encoding.)
4. "Restart Claude Code" can't be done headless. AGENTS.md 3.4 now says a new `claude` process loads the plugin and section 4 needs no session; new 3.5 explains `CLAUDE_CONFIG_DIR` for a test install and `--plugin-dir` for a session, since an empty config has no login.
5. Also found while fixing: README told readers to install "Python 3.11 or newer" while AGENTS.md, the README's own line above and the setup skill say 3.9. The README now says to install the current Python 3. Not tested on 3.9 itself (no 3.9 on this machine); a grep found no 3.10-only syntax.

Not tested by the agent: `--no-claude`, the MCP server, any skill run (they need a session).

These are docs-only changes after 7ee872a, so the code reviews of 7ee872a still cover the code that will be pushed.

## Release 0.1.0 (2026-11-20)

Released as v0.1.0 at commit 2631dda (the reviewed code of 7ee872a plus docs-only changes). The repo was created public with the MIT license, `main` and the annotated tag `v0.1.0` were pushed, and the release notes are the CHANGELOG's 0.1.0 section. readme-check `--kind tool` passed (0 fails, 0 warnings) both before and after the tag existed.

Install from GitHub, tested right after the release in an empty `CLAUDE_CONFIG_DIR` with Claude Code 2.1.330:

    > claude plugin marketplace add taosecurity/starfield-modding
    ✔ Successfully added marketplace: starfield-modding (declared in user settings)
    > claude plugin install starfield-modding@starfield-modding
    ✔ Successfully installed plugin: starfield-modding@starfield-modding (scope: user)
    3 userConfig options not yet set — run /plugin configure starfield-modding@starfield-modding in Claude Code, or pass --config KEY=VALUE.
    > claude plugin details starfield-modding@starfield-modding
      Skills (12)  build-mod, evaluate-mod, game-code-rules, log-review, logging-rules, new-mod, patch-day, rebuild-mod, release-check, setup, test-plan, wrap-up
      Hooks (1)  PreToolUse
      MCP servers (1)  papyrus-ref

All three commands exited 0. Still not tested: the interactive `/plugin configure` dialog.

## Planned rename to starfield-agent (2026-11-20)

The user wants the plugin called starfield-agent instead of starfield-modding (2026-11-20). The user chose to wait until the PMTGaps wrap-up is finished, because that session was editing the DD next steps and DevProcess, which name the plugin.

When the wrap-up is done, rename everything in one pass:

- This repo: the plugin and marketplace names in `.claude-plugin`, the skill prefix (`starfield-agent:build-mod` and so on), the MCP tool names, the settings file `.claude/starfield-modding.json` (becomes `.claude/starfield-agent.json`), the hooks, tests, README, AGENTS.md, DESIGN.md and CHANGELOG. Release it as 0.2.0, since the install commands change.
- GitHub: rename the repo to taosecurity/starfield-agent (GitHub redirects the old links), then the local folder.
- Elsewhere: the hub card in `tools\sites.json`, `tools\readme-check\repos.json`, the DD next-steps file `claude-code-plugin-starfield-modding.json`, DevProcess `content.py`, and the memory cards.
- Both reviews before the push, as usual.

- Handed off 2026-11-20: the PMTGaps master took the rename on as step R in `PMTGaps\WORKPLAN.md`, after the wrap-up W (PMTGaps commit 0cc60c5).
- Done in 0.2.0 (2026-11-21): every name in the plugin, docs, hooks and tests says starfield-agent. CHANGELOG 0.1.0 and the history in these notes keep the old name. The hooks and the MCP launcher read `starfield-agent.json` first and fall back to the old `starfield-modding.json` in the same place (project and user file), so 0.1.0 settings keep working; 5 new tests. 108 tests pass, `claude plugin validate` OK, readme-check OK.

## Release review (2026-11-20)

- Both guard policies stay as released: the game-code guard still refuses commits of `.psc` files with official script names, and a project's `.claude/starfield-modding.json` still can't set `papyrus_ref`.
- The plugin is listed on the Development Hub (https://taosecurity.github.io/), with a What's new item.
- Still untested: the interactive `/plugin configure` dialog, and a full real modding session with the stricter guards on.
- The throwaway test folders used by the release tests were deleted.
