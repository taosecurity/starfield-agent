---
name: game-code-rules
description: What may and may never be shared from Starfield - your own code, format facts and symbol names are fine; game executables, game files, official .psc sources, decompiled code and Ghidra projects never are. Says what the plugin's hook enforces and what it can't catch. Use before any commit, release, issue, post or chat message that carries code or files.
---

# Game code rules

Bethesda's code and files belong to Bethesda. Sharing them in a repo, a release, an issue or a post can get a mod or an account taken down, and it is never needed: everything a modder shares can be their own work plus facts about the format.

## May be shared

1. Your own scripts (`.psc` you wrote), builders, tools and plugins.
2. Facts about formats: record layouts, field meanings, flag values, how the game reads a file, written in your own words.
3. Symbol data: function and script names, Form IDs and Editor IDs, offsets. Names and numbers, not code.
4. Short quotes of a log line or an error message, when reporting a bug.

## Never shared

1. The game's executables and DLLs (`Starfield.exe`, the Creation Kit), and the game's own plugins and archives (`Starfield.esm`, `Constellation.esm`, `OldMars.esm`, `ShatteredSpace.esm`, `BlueprintShips-Starfield.esm`, `SFBGS*.esm`, `Starfield - *.ba2` and the add-ons' archives).
2. Official Papyrus sources (`.psc` from the Creation Kit's script sources), even one file, even edited.
3. Decompiled code of any kind: decompiled `.pex` scripts, decompiled game functions, pseudocode pasted from a decompiler.
4. Ghidra or IDA projects and databases of the game (`*.gpr`, `*.rep`, `*.i64`), and anything exported from them other than symbol names.
5. Caches made from Bethesda's sources, such as sf-papyrus-ref 0.1.0's local cache from `build-local`.
6. Saves and logs of other people, and your own only after reading them for names and paths.

## Steps before a commit, release or post

1. List what goes up: `git status` and `git diff --cached --name-only` for a commit, the zip's contents for a release, the text for a post.
2. Check each file against "Never shared". For a `.psc`, ask: did the user write it? A file with an official script's name (check with `python -I sf_papyrus_ref.py script <name>`) or one copied from the Creation Kit's sources is not theirs.
3. Add the game's files and build output to `.gitignore` (`*.esm` from the game, `*.ba2`, `*.sfs`, `*.gpr`, `*.rep`, `Scripts/Source/Base/`), so they can't be added by accident.
4. When explaining how the game works, describe it in your own words and name functions; don't paste decompiled code. If the user asks for decompiled code to be shared, say why it can't be and offer a written description instead.

## What the hook does, and what it can't

The plugin's `guard_game_code` hook runs before `git add`, `git commit`, `git push`, `gh release create` or `upload` and `gh gist create`. It refuses official plugins and archives by name, the game's and the Creation Kit's executables, the Creation Kit's `ContentResources.zip`, Ghidra and IDA databases, saves, and `.psc` files with official script names (from sf-papyrus-ref when installed; without it, only `.psc` files in the Creation Kit's `Scripts/Source/Base` folder). It reads the files inside a release `.zip` too. When a file's first lines look like decompiler output, it asks the user instead of refusing, because that test is a guess: say what the file is and let the user decide.

It can't catch decompiled code with the banner removed, code pasted into an issue, a post or a chat, game files renamed, or files sent any other way than git and the GitHub CLI. Those are up to the agent and the user: follow the steps above every time, hook or not. Never bypass a refusal (no `--no-verify`); fix what it found.
