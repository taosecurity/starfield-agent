---
name: log-review
description: Review a test session's logs for a Starfield mod - the sf-log-collector zip, Papyrus log rules, the test plan's log checks, crash logs and saves - and draft a result per tested mod. NOT SEEN means not tested, not failed. Use after a test session, when the user says the logs are ready, or asks to check a Papyrus log, crash log or save.
---

# Log review

The tester played, quit the game and ran sf-log-collector 2.0.1, which writes one zip with the Papyrus logs, SFSE and crash logs, INIs, `Plugins.txt` and, when asked, saves. This skill reads that zip and drafts a result for each mod that was tested. The tester marks the test plan; the agent only drafts.

## Steps

1. **Pick the right package.** The collector writes `Documents\StarfieldLogs\StarfieldLogs-<yyyyMMdd-HHmmss>-<note>.zip` (or the `-OutDir` folder the tester used). Take the newest one, and check that its time and note match the session the user described. If they don't match, ask before going on. If there is no package, tell the user how to make one (sf-log-collector's `AGENTS.md`, section 5): double-click `Collect-StarfieldTestLogs.cmd` after quitting the game, with `-IncludeSaves` or `-SavePair` when saves should be checked.

2. **Run papyrus-log-check 0.3.2 first**, straight on the zip (it reads it in memory):

   ```
   python -I papyrus_log_check.py "<StarfieldLogs-....zip>" --rules "<Mod>.logrules.json" --out "<report folder>"
   ```

   With several mods, repeat `--rules`, or use `--root "<projects folder>"` when each project keeps `testplan\logrules.json`. Add `--set-version "My Mod=0.9.1"` when the log is from an older build than the rule file. Start from its summary lines, then each FAIL and FLAG. **NOT SEEN means the feature wasn't tested in this session, not that it failed.** NOT LOADED means the plugin wasn't active in the package's `Plugins.txt`.

3. **Unpack the zip** into a new, empty scratch folder (never into the game or a repo) and read `manifest.json` first: the game, SFSE and plugin versions, the warnings, and the skipped files. A warning such as "No Papyrus.0.log found" means Papyrus logging was off (the `logging-rules` skill says how to turn it on), so every rule will be NOT SEEN.

4. **The test plan's log checks.** If the mod has a test plan (`test-plan` skill), turn the log report into marks with sf-test-plan 0.2.0:

   ```
   python -I sf_test_plan.py logs "<report folder>\logcheck-....json" --plan "<Mod>.testplan.md"
   ```

   It writes a `.marks.json` file the tester can import on the page. It marks only what the log rules prove and never replaces the tester's own marks. For each plan step that names a log line, say whether the line was seen, missing (and whether the tester marked the matching in-game step, since an unmarked step means not tested) or wrong.

5. **By hand, only where needed.** For a mod with no rule file, search the unpacked `Papyrus.0.log` for the mod's prefix (for example `[MyMod]`) and for `error` lines that name its scripts. Read the lines around each FAIL. Read the crash logs and `events.txt` in the package for crashes during the session, and say which module the crash log blames. A crash log naming a DLL is a lead, not proof.

6. **Saves, if the package has them.** Run sf-save-health 0.7.1 on the newest save, against the load order from the package:

   ```
   sf-save-health check "<unpacked>\saves\<save>.sfs" --plugins "<unpacked>\appdata\Plugins.txt"
   ```

   For a before/after pair (the collector's `-SavePair`), run `sf-save-health solo "<StarfieldLogs-....zip>"` and quote its verdict: it reports only what is new since the "before" save. Forms the save uses that the installed plugin no longer has are expected when a newer build removed them on purpose; check the mod's history (`git log -S"<form id>"`) before calling it a loss. For quest progress, sf-save-reader 0.1.3 shows the stages: `sf-save-reader quests "<save>.sfs" --data --filter "<plugin>" --details`, and `sf-save-reader compare "<before>.sfs" "<after>.sfs"` shows what changed. Never say a save is "safe" from exit code 0 alone: say what was checked.

7. **Draft one result per tested mod:** the build version, PASS, FAIL or NOT SEEN per rule, what was found by hand, the save verdict, and what to test next. Show the drafts to the user. Write them into the mod's `NOTES.md` or its test plan's results only after the user agrees.

**Check:** every mod the user named has a drafted result, or an explicit "not seen in this log".

## Never

- Copy logs or saves from the package into a repo that is pushed anywhere, or post them in public. Logs can hold the Windows user name, the character name and paths; tell the user to read a package before sharing it.
- Treat a missing log line as a failure without saying it could mean "not tested".
- Change, clean or "fix" a save. All three save tools are read-only, and so is this skill.
