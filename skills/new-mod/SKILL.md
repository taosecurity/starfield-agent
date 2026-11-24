---
name: new-mod
description: Start a new Starfield mod - pick the mod name, plugin name and script prefix, make the project folder with git, NOTES.md and a CLAUDE.md of mod rules, and a builder from the sf-mod-build template. Use when the user says "start a new mod" or "make a mod that ...".
---

# New mod

Makes a project that builds from the first day. Run the `setup` skill first if the game folder or the tools aren't known yet.

## Steps

1. **Understand the idea.** Ask what the mod should do in the game, in one or two sentences, and whether it is meant for Nexus Mods, Bethesda Creations (consoles too) or only the user's own game. Creations rules out SFSE, DLLs and INI changes, and allows only masters that are on Creations.

2. **Pick the names** (show them and get the user's OK):
   - Mod name: capitalized words, no spaces (`QuietOutposts`). The project folder, the plugin and the zip use it.
   - Plugin: `<ModName>.esm`. It must never end in an official plugin's name (`-ShatteredSpace.esm`, `-Constellation.esm`, `-Starfield.esm`, `-OldMars.esm`, `-SFBGS<nnn>.esm`) or start with `BlueprintShips-`: the game drops such names from `Plugins.txt` and the plugin stops loading. Use an `Addon` suffix instead (`QuietOutposts-ShatteredSpaceAddon.esm`).
   - Script prefix: two to four capital letters (`QO`), used for EditorIDs (`QO_Quest_Main`), the script folder and the log prefix (`[QO]`).
   - Version: start at `0.1.0`. Stay below 1.0.0 until it has passed a test.

3. **Check for similar mods.** Search Nexus Mods and Bethesda Creations for the idea. If one exists, tell the user and ask whether to build anyway, contribute, or drop it.

4. **Make the project** with sf-mod-build 0.4.1 (its `AGENTS.md` has the details):

   ```
   dotnet new sfmod -n QuietOutposts --prefix QO --mod-author "Your Name"
   cd QuietOutposts
   sf-mod-build validate
   sf-mod-build doctor
   ```

   The template's builder pins an exact BuildKit version in its project file (sf-mod-build 0.4.1's template pins 0.4.2, which is tested with Mutagen 0.54.4; the newest is BuildKit 0.5.0, which a builder moves to only when the user asks). Don't change the pins unless the user asks. Without .NET or the Creation Kit, say what is missing (from `doctor`) and stop here.

5. **Start git and the notes:**
   - `git init`, then a `.gitignore` that leaves out `dist/`, `.build/`, `creations-out/`, `*.zip`, `*.ba2`, `*.pex` and any copy of game files.
   - `NOTES.md`: what the mod does, the names from step 2, the target (Nexus, Creations, personal), and a "Next step" line.
   - `CLAUDE.md` for the project, holding the mod rules below so every later session sees them. The user may edit it.

6. **The mod rules** (write them into the project's `CLAUDE.md`):
   - Prefer a conflict-free design: no edits to vanilla records unless the design needs them; inject with scripts and use the mod's own records.
   - Every script logs with `Debug.Trace` and the mod's prefix, and the mod has its own Gameplay Options group with a "Show Debug Messages (PC only)" option, off by default (BuildKit `GameplayOptions.Debug`). Details: the `logging-rules` skill.
   - Text the player must see is a Message record shown with `Show()` (BuildKit `Messages.Hud` / `Messages.Box`), never `Debug.Notification` or `Debug.MessageBox`, which do nothing on Xbox and PlayStation.
   - Never compile Papyrus with `-release`: it strips every `Debug` call. sf-mod-build has no option for it.
   - Effect entries need EFIF and MUID or they never apply; BuildKit adds them. Keep FormIDs fixed with `IdLock` and commit `ids.lock.json`.
   - One plugin per zip; no `.psc` sources in the zip.
   - Test with a new character.
   - Never copy Bethesda's files, official `.psc` sources or decompiled code into the project or a release (the `game-code-rules` skill).

7. **First build.** Run the `build-mod` skill once, so the user sees the empty mod build and pass its checks before any feature work.

8. **Commit** (`git add -A`, `git commit -m "Start <ModName> 0.1.0 from the sfmod template"`) and report: the names, the folder, the first build's result, and the next step from `NOTES.md`.
