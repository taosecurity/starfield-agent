---
name: wrap-up
description: End a modding work session cleanly - update the project's NOTES.md (what changed, why, the next step), commit the finished and checked work with a clear message, and say what was committed. Never commits saves, game files, test zips or build output. Use at the end of a session, or when the user says to wrap up, save progress or commit.
---

# Wrap-up

The next session, yours or another agent's, starts from `NOTES.md` and the git log. This skill makes sure both say where the work stands.

## Steps

1. **See what changed:** `git status` and `git diff --stat` in the project folder. If nothing changed, say so and stop.

2. **Sort the changes.**
   - Finished and checked (it builds, its checks pass, or it was re-read): commit it.
   - Half done: leave it uncommitted, or commit it on a branch with "WIP" in the message, and say which in `NOTES.md`.
   - Never commit: saves (`*.sfs`), logs, test zips, `dist\` and `.build\` folders, the game's own files, official `.psc` sources, decompiled code, Ghidra projects (`game-code-rules` skill), and secrets (API keys, tokens, passwords). If any of these shows up in `git status`, add it to `.gitignore`.

3. **Update `NOTES.md`** at the top, with the date (`2026-11-20`, never "today"):
   - what changed and why, in a few lines;
   - the current version and its state (built, tested, passed, released);
   - check results (what was run and what it said), and anything not checked;
   - open questions for the user;
   - the one next step, concrete enough for a fresh session to start on.

   Keep history short: decisions and findings stay, step-by-step chatter goes.

4. **Commit** with a clear message: one line saying what the commit does, then a short body if the why isn't obvious.

   ```
   git add NOTES.md <the finished files>
   git commit -m "Add the credit reward to the quest's last stage"
   ```

   Add files by name rather than `git add -A` when the folder holds anything from the "never" list. If git has no identity set, ask the user for the name and email to use; don't invent one.

5. **Don't push** unless the user asked for it in this session. Pushing, tagging, releasing and uploading are the user's call (`release-check` skill for mods).

6. **Report** in a few lines: what was committed (the commit's short hash and message), what was left uncommitted and why, and the next step.

**Check:** `git status` after the commit shows only the files you meant to leave, and `NOTES.md` names the next step.
