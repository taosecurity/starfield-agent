---
name: rebuild-mod
description: Remake or fix another author's Starfield mod - permission first and written down, read the original read-only, match vanilla and sibling behavior with proper code instead of copying the original's quirks, credit the author, then build. Use when the user wants to rebuild, update, port or fix someone else's mod.
---

# Rebuild someone else's mod

A rebuild is new work on top of another author's idea. Their permission and credit come first, and the result should behave the way the game's own content does.

## Steps

1. **Permission.** Read the mod's page and files for its permission terms (Nexus Mods has a Permissions section). If they don't allow a rebuild or a release, the user asks the author. Write the answer in the project's `PERMISSION.md`: who, when, where (the message link or a screenshot), and any conditions. Without permission, the rebuild can be for the user's own game only; say so, and don't plan a release.

2. **Keep the original.** Put the downloaded archive in the project's `originals\` folder (git-ignored), and record its version and SHA-256 in `NOTES.md`. Unpack it into a folder of its own and treat it as read-only.

3. **Read it before changing it.** Run the `evaluate-mod` skill on the original. It shows the records, scripts, overrides of the game's records, and anything that undoes official changes. Read the author's README, changelog and open bug reports too.

4. **Plan the rebuild** in the project's `NOTES.md` and show it to the user:
   - what stays, what changes, and why;
   - for each behavior, how the game's own similar content does it (the vanilla records and sibling mods), so the rebuild matches the game, not the original's quirks;
   - records the original edits that a script and the mod's own records could do instead (conflict-free design);
   - the new names (`new-mod` skill, step 2). A rebuild gets its own plugin name, so it never replaces the original's in a load order by accident.

5. **Make the project** with the `new-mod` skill (steps 4 to 6), and write the new code. Never copy the original's compiled scripts into the new project, and never decompile them into it: write the scripts again from what the evaluation showed. Record each choice that differs from the original in `NOTES.md`.

6. **Build** with the `build-mod` skill.

7. **Compare with the original.**
   - Scripts: `python -I pex_compare.py compare "<original> - Main.ba2" "dist\<ModName> - Main.ba2"` (sf-pex-tools 0.1.0) shows which scripts differ in meaning.
   - Plugins: `sf-mod-check triage dist\<ModName>.esm` and `sf-mod-check triage <original plugin>` (sf-mod-check 0.9.0) side by side: records added, overridden, ITMs, official changes undone.
   - Check that every difference is one you planned.

8. **Credit.** The README names the original author and links their mod, says what the rebuild changes, and repeats any condition from `PERMISSION.md`. Keep `PERMISSION.md` out of the release zip (`sf-mod-check release --profile house` flags it).

9. **Bugs in the original.** Before telling the author their mod is broken, prove it: test the current version, rule out the user's own load order and mods, show the code actually runs, and write the evidence (version, steps, expected and actual result) in `NOTES.md`. If any of that can't be done, call it a suspicion, not a bug.

10. **Commit and report**: what was rebuilt, how it differs from the original, the check results, and the permission status.
