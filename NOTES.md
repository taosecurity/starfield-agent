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
