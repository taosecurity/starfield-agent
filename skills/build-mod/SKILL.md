---
name: build-mod
description: Build a Starfield mod into a test zip - check the design rules, compile Papyrus (optimize, never release), write the plugin, pack the archive and zip (one plugin per zip, no .psc), run the checks, and record the version. Use when the user asks to build, rebuild, bump or package a mod, or to get it ready to test.
---

# Build a mod

From source to a zip the user installs with their mod manager. The order matters: fix design problems before building, and fix every check failure before handing the zip over.

## Before building

1. **Read the project's `NOTES.md`** and check that the source is what you mean to build (`git status`, `git log -1`).

2. **Pick the version.** A number, bumped from the last build: `0.x.y` while untested, `1.0.0` once it passes a test. A quick experiment can be `<ModName>-spike-<version>.zip`. Write the version in `sfmod.json` (or the project's build script).

3. **The design checklist.** Fix any miss now:
   - every script logs with `Debug.Trace` and the mod's prefix, and the mod has its "Show Debug Messages (PC only)" option, off by default (`logging-rules` skill);
   - text the player must see is a Message record shown with `Show()`, not `Debug.Notification` or `Debug.MessageBox`;
   - no vanilla record edits unless the design needs them;
   - the plugin name is `<ModName>.esm` and doesn't end in an official plugin's name (`-ShatteredSpace.esm`, `-Constellation.esm`, `-Starfield.esm`, `-OldMars.esm`, `-SFBGS<nnn>.esm`) or start with `BlueprintShips-`;
   - the builder uses BuildKit 0.4.2 (`PluginWriter.Write`, `IdLock` with a committed `ids.lock.json`);
   - the README says what the mod does, how to install and uninstall it, and how to turn on Papyrus logging (in `StarfieldCustom.ini` under `[Papyrus]`: `bEnableLogging=1`, `bEnableTrace=1`, `bLoadDebugInformation=1`; the log is `Documents\My Games\Starfield\Logs\Script\Papyrus.0.log`).

## Build

4. **With sf-mod-build 0.1.1** (projects with `sfmod.json`):

   ```
   sf-mod-build build
   ```

   It compiles with the Creation Kit's compiler and `-optimize` (never `-release`), runs the builder, packs `<ModName> - Main.ba2` with Archive2, writes `<ModName>-<version>.zip` and runs sf-mod-check's `release` check on it. Add `--verbose` or `--log build-log.txt` to see why something failed; `sf-mod-build <step>` runs one step at a time (`compile`, `plugin`, `pack`, `zip`, `check`). Its `AGENTS.md` has every option.

   **Without sf-mod-build** (a project with its own build script): run that script, and make sure it compiles with `-optimize` and without `-release`, writes the plugin outside the game's `Data` folder, packs scripts into `<ModName> - Main.ba2`, and zips the plugin, the archive, the README and the license, with no `.psc` files.

5. **Checks, in this order.** Fix every ERROR, PROBLEM or FAIL before going on:
   - `sf-mod-check check dist\<ModName>.esm` (sf-mod-check 0.9.0): the plugin is sound. Read each WARNING against what the builder meant to do.
   - `sf-mod-check release <ModName>-<version>.zip`: the zip as a player gets it. Add `--profile house` to also fail on packaging rules (more than one plugin in a zip, `.psc` sources, a README with no mod name). An add-on's zip is checked together with its main mod's zip: `sf-mod-check release <Addon zip> <Main zip>`.
   - One plugin per zip: an add-on, patch or option gets its own zip, `<ModName>-<Part>-<version>.zip`. Mod managers install folders such as "Optional - ..." as they are, so plugins in them never load.
   - For Bethesda Creations only: set `"xbox": true` in `sfmod.json`, so the build also makes `creations-out\` with `<ModName> - Main_xbox.ba2`. Read every console warning (copied PC `.wem` audio is silent on consoles; `Debug` text never shows there). The Xbox archive never goes in the PC zip.

6. **Confirm the output is the build you just made.** Compare the zip's plugin with `dist\<ModName>.esm` (same SHA-256). Compare scripts by meaning, not bytes: every compile gives new bytes (sf-pex-tools 0.1.0, `pex_compare.py compare`).

## Hand over

7. **Record** in `NOTES.md`: the version, what changed and why, the check results, and what to test first. Commit the source (`git add -A`, `git commit`), never the zip, `dist\`, `.build\` or game files.

8. **Report** to the user: the version, what changed, the check results, the zip's path, and what to test first with a new character. Tell them to install the zip with their mod manager (Vortex: drop it on the Mods page; MO2: Install a new mod from an archive); the agent never copies it into `Data`. For a test session, the `test-plan` skill writes the checks.
