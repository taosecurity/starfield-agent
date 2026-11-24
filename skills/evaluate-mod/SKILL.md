---
name: evaluate-mod
description: Evaluate a Starfield mod read-only - what a downloaded mod does (records, scripts, files, overlap with the user's mods, permissions), or what changed between two versions and whether it affects the user's own mods and load order. Use for "what does this mod do?", "is this update safe for my mods?" or "what changed in this update?".
---

# Evaluate a mod

Read-only toward the mod and the game: nothing is installed, rebuilt or reported to its author from this skill. The answer is a plain report, never a verdict that a mod is "safe".

## Steps

1. **Find the files.** Ask for the downloaded archive (or the mod's folder in the mod manager). Unpack it into a new, empty folder outside the game's `Data` folder, one folder per version: `<work folder>\<ModName>\<version>\`. Treat it as untrusted: never run its programs or scripts.

2. **Seen before?** Look in the user's projects for the mod's name: `NOTES.md` files, `originals\` folders, `PERMISSION.md`. If an older copy exists, this is an update (step 5); otherwise a first evaluation (steps 3 and 4).

3. **First evaluation.** Run sf-mod-check 0.15.2's triage on the archive:

   ```
   sf-mod-check triage "<download>.zip" --out "<work folder>\<ModName>\triage"
   ```

   Open its `.html` report. It lists every file with its SHA-256, what the mod replaces in the game's own files, each plugin's masters, added and overridden records, ITMs, deleted records, official changes it undoes, its compiled scripts (what each calls, whether it logs) and its DLLs. Read the LOOK lines first and report them as "worth a look", never as faults. Then `sf-mod-check check <plugin> --data "<game>\Data"` for each plugin. For records worth a closer look, sf-cut-check 0.2.0's `find` and `why` (optional) say whether a record is cut content the game never uses.

4. **Overlap with the user's setup.**
   - Load order: sf-load-order 0.2.2 on the user's order with the new mod in it (`sf-load-order.cmd`, or `--mo2 "<instance>"`, or `--vortex-loadorder "<exported file>"`) reports missing masters, known clashes, archive and loose-file overlap, and record conflicts.
   - Record conflicts in detail: `sf-mod-check conflict` (or `--plugins "<Plugins.txt>"`).
   - The user's own mods: which of their projects use records, scripts or files from this mod.
   - Permissions: the mod page's permission terms, and any `PERMISSION.md` the user already holds.

5. **An update: compare the versions.**
   - Files: list both folders with SHA-256 and report added, removed and changed files.
   - Scripts: `python -I pex_compare.py compare "<old> - Main.ba2" "<new> - Main.ba2"` (sf-pex-tools 0.1.0) reports scripts that differ in meaning, with a diff of the listing. Byte compares are useless for compiled scripts.
   - Archives: `python -I ba2_extract.py diff "<old>.ba2" "<new>.ba2"` lists new, removed and changed files.
   - Plugins: triage both versions (step 3) and compare the record lists: added, removed, changed records and which fields changed.

6. **Say what it means.** Plainly, change by change: what it does in the game. Then whether it affects the user's work: records or scripts their mods copied or depend on, features they ported from it (which may now need the update), new conflicts with their mods, and whether the mod is in their load order.

7. **Record** the findings in the affected project's `NOTES.md`, keep the new archive next to the old one in `originals\`, and commit. If the evaluation suggests a bug in the mod, the proof steps in the `rebuild-mod` skill (step 9) come before any report to its author.
