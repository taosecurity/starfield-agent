# Changelog

## 0.2.1 (2026-11-23)

### What's new

The setup skill and the guard now match the current tools.

- The setup skill checks sf-save-health with `sf-save-health --version` (new in sf-save-health 0.7.4) instead of `--help` with an exit code of 3. Its tool table and the README name the current release of every tool, and each check exits 0.
- The skills now use the current commands of the tools they name, and the guard lets the commands of sf-pex-tools (`pex_compare.py dump`, `ba2_extract.py where`), sf-papyrus-ref (`list`, `data`), sf-mod-check (`diff`, `gap`) and the `--version` of sf-save-health and sf-test-plan read the game's folders. `ba2_extract.py extract` is still refused there, because it writes.
- The new-mod skill now names the BuildKit version that sf-mod-build's template really pins (0.4.2).

### Example

The guard still refuses an extraction from the game's Data folder, and now lets the read-only commands through. This is its real output:

    > python -I hooks/guard_game.py < extract-from-data.json
    starfield-agent guard: refused a command that names the game's Data folder (Steam): in the part `python -I ba2_extract.py extract "C:/Program Files (x86)/Steam/steamapps/common/Starfield/Data/x.ba2"`, `ba2-extract extract` is not one of its read-only modes. Commands that name these folders may only read them.
    Copy the file in yourself or install it with your mod manager; the agent only reads these folders. To guard more folders or point at a moved install, see the starfield-agent README, "Settings".
    exit 2

### Fixed

- The guard refused a write into a guarded folder only when the output option and its folder were two words. It now reads `--out="C:\My Games\..."` as one word, as the shells do, so a quoted path with spaces after `=` is checked too.
- `sf-save-reader extract <save> <out.bin>` writes a file, so the guard no longer lets it write into the saves folder; the reading commands (`dump`, `walk`, `records`, `quests`, `compare`) still work there.
- `sf-save-health solo --reports <folder>` can no longer point its reports into a guarded folder.

## 0.2.0 (2026-11-21)

### What's new

The plugin is now called starfield-agent. The skills, the hooks and the Papyrus lookup server work as before; only the names change.

- Install it with `/plugin marketplace add taosecurity/starfield-agent`, then `/plugin install starfield-agent@starfield-agent`.
- The skills are now `/starfield-agent:setup`, `/starfield-agent:build-mod` and so on.
- The MCP tools are now `mcp__plugin_starfield-agent_papyrus-ref__papyrus_lookup` and so on.
- The settings files are now `.claude/starfield-agent.json` in a project and `starfield-agent.json` in your own settings folder.

### Upgrading from starfield-modding 0.1.0

- Remove the old plugin with `/plugin uninstall starfield-modding@starfield-modding` and its marketplace with `/plugin marketplace remove starfield-modding`, then install starfield-agent.
- Plugin options set for the old plugin don't carry over. Set them again with `/plugin configure starfield-agent@starfield-agent`.
- The GitHub repository moved to https://github.com/taosecurity/starfield-agent, and the old address forwards there.
- Your settings files keep working. The old `starfield-modding.json` files are read after both new `starfield-agent.json` files, with the same rules: their guarded folders add up with the rest (to unguard a folder, remove it from the old file too, or delete the old file), their other values count only where neither new file sets them, and a project's old file still can't set `papyrus_ref`.
- The `setup` skill keeps your old file's values when it writes the new one, then offers to delete the old file.

### Example

The guard's refusal now names the new plugin. This is its real output when the assistant tries to write a plugin into the game's Data folder:

    starfield-agent guard: refused to change C:\Program Files (x86)\Steam\steamapps\common\Starfield\Data\MyMod.esm, because it is in the game's Data folder (Steam).
    Copy the file in yourself or install it with your mod manager; the agent only reads these folders. To guard more folders or point at a moved install, see the starfield-agent README, "Settings".

## 0.1.0 (2026-11-20)

### What's new

This is the first release. starfield-modding is a Claude Code plugin for Starfield mod authors: it gives your AI assistant skills for the jobs a mod repeats, guard hooks that keep it out of your game's Data and saves folders, and a Papyrus lookup server.

Install it inside Claude Code with `/plugin marketplace add taosecurity/starfield-modding`, then `/plugin install starfield-modding@starfield-modding`, and run `/starfield-modding:setup` first.

### Example

    > python -I hooks/guard_game.py < write-into-data.json
    starfield-modding guard: refused to change C:/Program Files (x86)/Steam/steamapps/common/Starfield/Data/MyMod.esm, because it is in the game's Data folder (Steam).
    Copy the file in yourself or install it with your mod manager; the agent only reads these folders. To guard more folders or point at a moved install, see the starfield-modding README, "Settings".
    exit 2

    > python -I selftest.py
    ...
    selftest: 103 tests, OK
    ✔ Validation passed
    selftest: claude plugin validate OK
    RESULT: OK

### Skills

- `setup` finds the game, saves and mod manager, saves the settings and lists the modding tools you have.
- `new-mod`, `build-mod` and `rebuild-mod` start, build and remake mods with sf-mod-build, BuildKit and sf-mod-check.
- `evaluate-mod` says what a mod does, or what changed in an update, and whether it touches your mods.
- `test-plan` and `log-review` plan a test session and read its logs.
- `release-check` checks a zip before an upload to Nexus Mods or Bethesda Creations.
- `patch-day` checks SFSE plugins, your mods and your load order after a game update.
- `logging-rules`, `game-code-rules` and `wrap-up` hold the logging rules, the never-share-game-code rules and the end-of-session routine.

### Hooks and MCP

- The Data and saves guard refuses changes to the game's Data folder, the saves folder, `Plugins.txt` and `ContentCatalog.txt`, and lets reading commands and the tools' read-only modes through.
- The game-code guard refuses commits, pushes, releases and gists that carry official plugins, archives, executables, official script sources, saves or Ghidra and IDA databases, and asks first about files that look like decompiler output.
- The `papyrus-ref` MCP server runs sf-papyrus-ref 0.1.0 when it is installed, and a help-only stub when it is not.
- Settings come from environment variables, the plugin's options, a project file or a user file (see the README, "Settings"). A project file can add guarded folders but can't remove one or choose the program the hooks run.
- Set `SFMOD_HOOK_LOG` to a file path to get a troubleshooting log of what the guards read and decided.
