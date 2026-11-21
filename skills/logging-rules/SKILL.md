---
name: logging-rules
description: The logging rules for Starfield Papyrus scripts - Debug.Trace with the mod's prefix in every script, a "Show Debug Messages (PC only)" option off by default, player text as a Message record with Show(), never compile with -release, and README text on turning on Papyrus logging. Use when writing or reviewing Papyrus, or adding logging to a mod.
---

# Logging rules

A test is only as good as what the log can prove. These rules make every mod's behavior readable in `Papyrus.0.log`, and keep debug text off consoles, where it doesn't work.

## Rules

1. **Every script logs with the mod's prefix.** Use one short prefix per mod, in brackets, and trace each decision a tester would want to see: the quest starting, an item given, a check that passed or failed and why.

   ```papyrus
   Function Log(string msg)
       Debug.Trace("[MyMod] " + msg)
   EndFunction
   ```

   Log facts with values (`Log("gave " + count + " credits, total " + total)`), not just "here". Each line a script writes can become a log rule for papyrus-log-check 0.3.2 and a log check in the test plan (`test-plan` skill).

2. **A debug switch for on-screen messages.** The mod has its own Gameplay Options group with one option, "Show Debug Messages (PC only)", off by default, backed by a global variable the scripts read. On-screen debug text appears only when it is on:

   ```papyrus
   GlobalVariable Property MyMod_ShowDebug Auto Const Mandatory

   Function DebugNote(string msg)
       Log(msg)
       If MyMod_ShowDebug.GetValue() > 0
           Debug.Notification("[MyMod] " + msg)
       EndIf
   EndFunction
   ```

   In a BuildKit 0.4.2 builder, `GameplayOptions.Debug(...)` makes the option (off by default) and `GameplayOptions.Group(...)` the mod's group; its README shows both. Console commands can't find a light plugin's quests or globals by name, so a console `set` command is no substitute for the option.

3. **Text the player must see is a Message record**, shown with `Show()`. The `Debug` script does nothing on Xbox and PlayStation, so `Debug.Notification` and `Debug.MessageBox` are for debug text only. `Debug.Trace` and the debug switch stay in the mod; the README calls them PC only.

4. **Never compile with `-release`.** It strips every `Debug` call, including the traces. Compile with `-optimize` (the `build-mod` skill and sf-mod-build 0.1.1 do).

5. **The README tells players how to turn on Papyrus logging.** Use this text:

   > To send a useful bug report, turn on Papyrus logging. In `Documents\My Games\Starfield\StarfieldCustom.ini` (make the file if it isn't there), add:
   >
   > ```ini
   > [Papyrus]
   > bEnableLogging=1
   > bEnableTrace=1
   > bLoadDebugInformation=1
   > ```
   >
   > Start the game, play until the problem happens, and quit. The log is `Documents\My Games\Starfield\Logs\Script\Papyrus.0.log`. Lines from this mod start with `[MyMod]`. To see its messages on screen too, turn on "Show Debug Messages (PC only)" in Settings, Gameplay, under the mod's name.

6. **A mod with no scripts** (records only) gets neither the traces nor the switch, because nothing runs to log. The rules apply again as soon as it gains a script.

## Checking a mod against these rules

1. Search its `.psc` files for `Debug.Trace` and the prefix: every script should have at least one.
2. Search for `Debug.Notification` and `Debug.MessageBox` outside the debug helper. Each one that the player needs to see becomes a Message record.
3. Run sf-papyrus-ref 0.1.0 on the scripts: `python -I sf_papyrus_ref.py check "<mod folder>" --allow Debug.Trace`. It lists debug-only, beta-only and latent calls. For a Creations release add `--creations` (`release-check` skill).
4. Check the build settings for `-release` and the README for the logging section.

Report each miss with the file and line, and the fix.
