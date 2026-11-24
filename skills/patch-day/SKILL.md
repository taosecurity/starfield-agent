---
name: patch-day
description: After a Starfield game update, check which SFSE plugin DLLs still load, whether the update changed the records your own mods rely on (rebuild or not), and whether the load order still holds, then write one summary. Use after a game update, before installing an SFSE plugin download, or when the user asks what an update broke.
---

# Patch day

A game update can stop SFSE plugins from loading and can change records, quest stages or script functions that a mod depends on. This skill runs the checks in one pass and says what needs action. Everything here is read-only.

## Before an update (once per mod, and again after each rebuild)

1. **Take a drift baseline** for each of your own mods, with sf-patch-day 0.2.2, while the old game version is still installed:

   ```
   python -I sf-patch-day.py drift init "<MyMod.esm>" -o mods.json
   python -I sf-patch-day.py drift snapshot --mods mods.json -o baseline.json
   ```

   `init` finds the master records the plugin overrides. Add the quest stages and script functions the mod relies on by hand (the README's "The mods file"). Keep both files in the mod's project folder and commit them. Never rerun `snapshot --force` after the update: that throws away the baseline the check needs.

## After an update

1. **The game version.** Note the new version (shown on the main menu, or the version of `Starfield.exe`). If the user plays from a mod manager, close it before reading files.

2. **SFSE plugins:**

   ```
   python -I sf-patch-day.py dlls
   ```

   Add `--game "<folder holding Starfield.exe>"` for an unusual install, or a Mod Organizer 2 mods folder as the path (`"%LOCALAPPDATA%\ModOrganizer\Starfield\mods"`). Exit 0 means every plugin should load; 1 means some need the Address Library, a newer SFSE or may fail; 2 means some are locked to another game version, or it is a Game Pass install (SFSE doesn't support Game Pass). For a download not installed yet, give its zip as the path. "MAY FAIL" needs an in-game test; it isn't a verdict.

3. **Drift, for each of your own mods** with a baseline:

   ```
   python -I sf-patch-day.py drift check --mods mods.json --baseline baseline.json
   ```

   Exit 0: nothing the mod uses changed. Exit 1: something changed but the mod doesn't use it, or there is a name to check by hand. Exit 2: rebuild (records, stages or functions the mod relies on changed). Add `--plugin-dir "<folder>"` when masters live in a mod manager's folder. With no baseline, say so, and take one now for the next update.

4. **The load order**, with sf-load-order 0.2.2 (it finds Steam and Game Pass by itself):

   ```
   .\sf-load-order.cmd --depth light
   ```

   Mod Organizer 2: add `--mo2 "<MO2 instance folder>"`. Vortex: have the user export the Load Order page first, then `--vortex-loadorder "<exported file>"`. It flags patches built for an older version of a master and plugins whose masters went missing. Read `sf-load-order-report\report.txt`. Never apply a suggested order without the user agreeing.

5. **Write one summary**, in this order: DLLs that won't load (and what they wait for: SFSE, the Address Library, the author), own mods that need a rebuild (with the changed records), load order problems, and what is fine. For each item, say the one next action: wait for an update, rebuild with the `build-mod` skill, or turn the mod off for now.

**Check:** every SFSE plugin and every one of the user's own mods is named in the summary, with a result or a reason it wasn't checked.

## Never

- Edit plugins, move or delete DLLs, turn mods on or off, or download anything. The user does those with their mod manager.
- Roll back the game. Tell the user what the checks found and let them decide.
