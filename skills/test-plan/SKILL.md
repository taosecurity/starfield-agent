---
name: test-plan
description: Write a test plan for a Starfield mod build with sf-test-plan - steps for a new character, a few smoke checks, and a Papyrus log rule for each check the log can prove - and build it into a tick-off HTML page. Use before a test session, or when the user asks for a test plan or checklist.
---

# Test plan

A test plan says what to try in the game and what should happen, in an order a player can follow with a new character. sf-test-plan 0.4.0 turns it into one HTML page the tester ticks off; its `AGENTS.md` and `FORMAT.md` have the exact format.

## Steps

1. **Read the mod.** Its `NOTES.md` (what changed in this build, what to test first), its README and its scripts' `Debug.Trace` lines. Each trace line the scripts write is a fact the log can prove.

2. **Start the plan** in the project folder, if there isn't one yet:

   ```
   python -I sf_test_plan.py new <ModName>.testplan.md --mod "<Mod Name>"
   ```

   (Run it from the sf-test-plan folder, or give the full path to `sf_test_plan.py`.) For a new build of a mod that has a plan, change its `run:` line to `<mod>-<version>` and its `version:` and `zip:` lines; the page then starts with empty marks.

3. **Write the steps**, following `FORMAT.md` section 1:
   - `## Before you start`: install the zip with the mod manager, turn on Papyrus logging (the README's steps), and start a new character. Unreleased mods are tested with new characters, so old saves need no care.
   - Groups `## <n> <title>`, in the order a player meets the features. Each step is `- [ ] <what to do>` with an indented `Expect: <what should happen>`. Put console commands in backticks.
   - Mark the five to eight steps that show the build basically works as `smoke: yes`.
   - The debug option: one step turns on "Show Debug Messages (PC only)" in the mod's Gameplay Options group and checks a message appears.
   - Uninstall: the last group removes the mod and loads the save, when the mod is meant to be removable.

4. **Log rules.** For each step the Papyrus log can prove, add `log: <id>` to the step and a rule with that id to `<ModName>.logrules.json`, the rule file papyrus-log-check 0.4.2 reads (sf-test-plan's `examples/Beacon.logrules.json` shows the shape): `mod`, `version`, `plugins`, `prefix`, an `expect` list (lines the step should cause, each with `id`, a regular expression `re`, a sample `show` and what it `means`) and a `forbid` list (lines that must never appear). A rule that sees nothing reports NOT SEEN, which means "not tested", not "failed".

5. **Check and build:**

   ```
   python -I sf_test_plan.py check <ModName>.testplan.md --rules <ModName>.logrules.json
   python -I sf_test_plan.py build <ModName>.testplan.md --rules <ModName>.logrules.json
   ```

   Fix every `error` from `check`; read each `warning`. `build` writes `<ModName>.testplan.html` next to the plan.

6. **Commit** the plan and its rules (not the HTML page if the project ignores build output), and tell the user where the page is. After the test, the tester exports the marks from the page; `python -I sf_test_plan.py import <marks file> --plan <ModName>.testplan.md` adds them to the results, and the `log-review` skill reads the logs.
