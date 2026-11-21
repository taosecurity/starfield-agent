# Changelog

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
