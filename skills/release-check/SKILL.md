---
name: release-check
description: Check a Starfield mod's release zip before an upload to Nexus Mods or Bethesda Creations - the sf-mod-check release check, permission and credits, README, naming, one plugin per zip, and for Creations the console rules - then list the archive's contents. The user does the upload. Use before any mod upload or when the user asks whether a mod is ready to release.
---

# Release check

The last look before a mod goes public. The agent checks and reports; the user uploads. Run it on the exact zip that will be uploaded, made by the `build-mod` skill.

## Steps

1. **Confirm it is the current build.** The zip's name is `<ModName>-<version>.zip`, the version matches `NOTES.md` and the last commit, and the plugin inside has the same SHA-256 as the one just built (`build-mod` step 6). A release version is `1.0.0` or later, after the mod passed a test.

2. **Run the release check** with sf-mod-check 0.15.2:

   ```
   sf-mod-check release <ModName>-<version>.zip --profile house
   ```

   `--profile house` also fails on packaging rules (more than one plugin, `.psc` sources, a README with no mod name, private files such as permission notes) that the default `basic` profile only warns about. An add-on is checked together with its main mod: `sf-mod-check release <Addon zip> <Main zip>`. The result must be `RESULT: OK`. Fix every PROBLEM line and read every REVIEW line. Its `AGENTS.md` has the other options.

3. **Permission and credits.** If the mod uses another author's work (a rebuild, a patch, borrowed assets or scripts), their permission must be written down in the project (the author's words, where and when they said it) and match what the mod does. Check the mod page's terms too: some authors allow patches but not re-uploads. The README credits every author whose work is in it. With no permission on record, stop: the release waits.

4. **The README** says what the mod does, its requirements (masters and their versions), how to install and uninstall it, known limits, credits, the license, and how to turn on Papyrus logging (the `logging-rules` skill has the text). A mod with no scripts needs no logging section.

5. **Names and layout.**
   - One plugin per zip. Add-ons, patches and options each get their own zip, `<ModName>-<Part>-<version>.zip`, with no "Optional - ..." folders.
   - The plugin is `<ModName>.esm` with no spaces, and doesn't end in an official plugin's name (`-ShatteredSpace.esm`, `-Constellation.esm`, `-Starfield.esm`, `-OldMars.esm`, `-SFBGS<nnn>.esm`) or start with `BlueprintShips-`, because the game drops such names from `Plugins.txt`.
   - No `.psc` sources, saves, logs, game files or build folders in the zip (`game-code-rules` skill).

6. **For Bethesda Creations, also:**
   - Check the scripts with sf-papyrus-ref 0.2.3, so calls that do nothing on consoles count as errors:

     ```
     python -I sf_papyrus_ref.py check "<mod folder>" --allow Debug.Trace --creations --json
     ```

     It must exit 0. Text the player must see is a Message record shown with `Show()`; `Debug.Notification` and `Debug.MessageBox` do nothing on Xbox and PlayStation.
   - No SFSE, DLL or INI. Every required master is itself on Creations (the base game and its official add-ons count); anything else is optional in code (`Game.IsPluginInstalled`).
   - Shipped audio needs PC, Xbox and PlayStation versions made by the Creation Kit from WAV sources. PC `.wem` files copied over are silent on consoles; the game's own sounds are fine.
   - The build made `<ModName> - Main_xbox.ba2` (`build-mod` step 5).
   - The Creation's description carries the README's credits, license and Papyrus logging notes (logging works on PC only).

7. **List the zip's contents** for the user (every file with its size), so they see exactly what goes up.

## Report

The checklist with a result for each step (done, or why not), the `RESULT:` lines, the contents list, and anything the user must decide. Then stop: the user uploads. Never upload, never log in to Nexus Mods or Bethesda.net for the user, and never change a mod page.
