"""starfield-agent guard: keep the agent from changing the game's Data folder, the saves and Plugins.txt.

A Claude Code PreToolUse hook (DESIGN.md section 4.1). It reads the tool call as JSON on stdin and exits 2 with a
reason on stderr to refuse it, or 0 to let the normal permission rules decide.

- Edit, Write, MultiEdit and NotebookEdit: refused when the file is inside a guarded folder or is a guarded file.
- Bash and PowerShell: a command that names a guarded path (or runs with its working folder inside one) is let
  through only when every part of it is a read-only command from the table below and nothing is redirected
  into a file. Everything else that names a guarded path is refused.

What is guarded and how to add folders: hooks/sfmod_config.py and the README's "Settings" section.
It never changes anything itself. Standard library only.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfmod_config as cfg  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
# Read-only commands. A name maps to None (any arguments) or to the set of first words (subcommands) that only
# read. Names are compared in lower case with any folder, ".exe", ".py", ".cmd", ".bat" or ".ps1" removed and
# "_" read as "-", so "python -I sf_papyrus_ref.py check" and "sf-papyrus-ref.cmd check" are the same entry.
# ---------------------------------------------------------------------------------------------------------------
READ_ONLY_PLAIN = {
    # listing and reading
    "ls": None, "dir": None, "gci": None, "get-childitem": None, "cat": None, "type": None, "gc": None,
    "get-content": None, "test-path": None, "get-item": None, "gi": None, "get-itemproperty": None,
    "resolve-path": None, "split-path": None, "file": None, "stat": None, "du": None, "tree": None,
    "head": None, "tail": None, "less": None, "more": None, "wc": None, "grep": None, "rg": None,
    "findstr": None, "select-string": None, "sort": None, "echo": None, "write-output": None,
    # moving around (the guard follows these to know each part's working folder)
    "cd": None, "set-location": None, "sl": None, "pushd": None, "popd": None, "chdir": None, "pwd": None,
    "get-location": None,
    # hashes
    "sha256sum": None, "sha1sum": None, "md5sum": None, "get-filehash": None,
    # PowerShell filters that only shape output
    "select-object": None, "where-object": None, "sort-object": None, "measure-object": None,
    "format-table": None, "format-list": None, "out-null": None, "out-string": None,
}
READ_ONLY_TOOLS = {
    "sf-mod-check": {"check", "conflict", "triage", "release", "diff", "gap", "--version", "--help", "-h"},
    "sf-save-health": {"check", "solo", "--version", "--help", "-h"},
    "sf-save-reader": None,
    "sf-cut-check": {"find", "scan", "why", "--version", "--help", "-h"},
    "sf-load-order": None,
    "sf-patch-day": {"dlls", "drift", "--version", "--help", "-h"},
    # sf-pex-tools' own commands (pex_compare.py, ba2_extract.py); `ba2_extract.py extract` writes, so it is not listed
    "pex-compare": {"compare", "dump", "--version", "--help", "-h"},
    "ba2-extract": {"diff", "list", "where", "--version", "--help", "-h"},
    "sf-papyrus-ref": {"check", "script", "lookup", "list", "data", "--version", "--help", "-h"},
    "papyrus-log-check": None,
    "sf-test-plan": {"logs", "check", "--version", "--help", "-h"},
    "sf-log-collector": {"zip", "--version", "--help", "-h"},
}
# Options whose value is where a command writes. A read-only command may read a guarded path, never write to one.
OUTPUT_OPTIONS = {"--out", "-o", "--output", "--log", "--report", "--state", "--dest", "--to", "--save",
                  "-outfile", "--json-out", "--html", "--csv"}
# Shell words that change files no matter what follows (checked so the message can name them).
WRITERS_PS = re.compile(r"\b(out-file|set-content|add-content|tee-object|new-item|copy-item|move-item|"
                        r"remove-item|rename-item|clear-content)\b", re.I)

# PowerShell script blocks, sub-expressions, static .NET calls and method calls can change files from inside a
# command that is otherwise on the read-only list (Where-Object { $_.Delete() }). Quoted text is removed first,
# so "Program Files (x86)" passes (double-quoted $(...) is refused earlier as command substitution).
CODE_IN_COMMAND = re.compile(r"[{}]|::|\.\w+\s*\(|(^|[\s=,|])\(")

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

ADVICE = ("Copy the file in yourself or install it with your mod manager; the agent only reads these folders. "
          "To guard more folders or point at a moved install, see the starfield-agent README, \"Settings\".")


def refuse(message):
    cfg.log("data guard", "refused: " + message)
    sys.stderr.write("starfield-agent guard: " + message + "\n" + ADVICE + "\n")
    sys.exit(2)


# --------------------------------------------------------------------------------------------- shell parsing

def split_command(command):
    """Split a shell command into parts on ; & && || | and newlines outside quotes.
    Returns (parts, flags); flags holds 'subst' (command substitution) and 'redirect' (output to a file)."""
    parts, flags, buf = [], set(), []
    i, quote, n = 0, None, len(command)
    while i < n:
        c = command[i]
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            elif quote == '"' and c == "$" and command[i + 1:i + 2] == "(":
                flags.add("subst")
            i += 1
            continue
        if c in "'\"":
            quote = c
            buf.append(c)
        elif c == "\\" and i + 1 < n and command[i + 1] in " \n":
            buf.append(" " if command[i + 1] == " " else "")
            i += 1
        elif c in ";\n|&":
            if c == "&" and buf and buf[-1] == ">":      # 2>&1 and >& are redirections, not separators
                buf.append(c)
            else:
                parts.append("".join(buf))
                buf = []
                if command[i:i + 2] in ("&&", "||"):
                    i += 1
        elif c == "$" and command[i + 1:i + 2] == "(" or c == "`" or c == "<" and command[i + 1:i + 2] == "(":
            flags.add("subst")
            buf.append(c)
        else:
            buf.append(c)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()], flags


HARMLESS_REDIRECT = re.compile(r"(\d?>&\d|\d?>>?\s*(/dev/null|\$null|nul)\b)", re.I)


def has_redirect(part):
    """True when a part sends output into a file (quotes removed first; 2>&1 and >/dev/null are harmless)."""
    unquoted = re.sub(r"'[^']*'|\"[^\"]*\"", "", part)
    unquoted = HARMLESS_REDIRECT.sub("", unquoted)
    return ">" in unquoted


def words(part):
    """Split one part into words, keeping quoted text together and removing the quotes."""
    out = []
    for m in re.finditer(r"\"([^\"]*)\"|'([^']*)'|(\S+)", part):
        out.append(next(g for g in m.groups() if g is not None))
    return out


def program_and_args(ws):
    """Skip env assignments, PowerShell's call operator and a Python launcher; return (program, args)."""
    i = 0
    while i < len(ws) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ws[i]):
        i += 1
    if i < len(ws) and ws[i] in ("&", "."):
        i += 1
    if i < len(ws) and re.match(r"^(python3?|py|python\.exe|py\.exe)$", os.path.basename(ws[i]).lower()):
        i += 1
        while i < len(ws) and ws[i].startswith("-"):
            if ws[i] in ("-m", "-c"):
                break
            i += 2 if ws[i] in ("-X", "-W") else 1
        if i < len(ws) and ws[i] == "-m":
            i += 1
    if i >= len(ws):
        return "", []
    name = re.split(r"[\\/]", ws[i])[-1].lower()
    name = re.sub(r"\.(exe|py|cmd|bat|ps1)$", "", name).replace("_", "-")
    return name, ws[i + 1:]


def part_is_read_only(part, cwd, roots):
    """Return None when the part only reads, else the reason it doesn't."""
    if has_redirect(part):
        return "it redirects output into a file"
    m = WRITERS_PS.search(part)
    if m:
        return f"it uses {m.group(1)}, which changes files"
    unquoted = re.sub(r"'[^']*'|\"[^\"]*\"", "", part)   # $(...) in double quotes is caught as "subst"
    if CODE_IN_COMMAND.search(unquoted):
        return "it runs code inside the command (a { } script block, ( ) expression, :: or .Method() call)"
    ws = words(part)
    name, args = program_and_args(ws)
    if name in READ_ONLY_PLAIN:
        if name == "sort" and any(a == "-o" or a.startswith("--output") for a in args):
            return "sort -o writes a file"
        return None
    if name in READ_ONLY_TOOLS:
        modes = READ_ONLY_TOOLS[name]
        first = next((a for a in args if not a.startswith("-") or a in ("--version", "--help", "-h")), "")
        if modes is not None and first.lower() not in modes:
            return f"`{(name + ' ' + first).strip()}` is not one of its read-only modes"
        for idx, a in enumerate(args):
            key, _, inline = a.partition("=")
            if key.lower() in OUTPUT_OPTIONS:
                value = inline or (args[idx + 1] if idx + 1 < len(args) else "")
                if value and cfg.guarded_reason(cfg.norm_path(value, cwd), roots):
                    return f"its {key} option points into a guarded folder"
        return None
    return f"'{name or part}' is not on the guard's read-only list"


GLOB_CHARS = re.compile(r"[*?\[]")
CD_COMMANDS = ("cd", "set-location", "sl", "pushd", "chdir")
# Folders that hold a guarded folder: deleting or moving one of them changes the guarded folder too.
PARENT_TAILS = ("/data", "/starfield/data", "/content/data", "/starfield/content/data", "/saves",
                "/starfield/saves", "/plugins.txt")


def parts_with_cwd(command, cwd):
    """[(part, working folder for that part)], following cd, Set-Location, pushd and chdir."""
    parts, _ = split_command(command)
    out, here = [], cwd
    for part in parts:
        out.append((part, here))
        name, args = program_and_args(words(part))
        targets = [a for a in args if not a.startswith("-")]
        if name in CD_COMMANDS and targets and here:
            target = cfg.expand(targets[-1])
            here = target if os.path.isabs(target) or re.match(r"^[A-Za-z]:", target) else os.path.join(here, target)
    return out


def holds_guarded(normalized, roots):
    """A label when a normalized path is a folder that holds a guarded folder (a parent up to two levels up)."""
    if not normalized:
        return None
    base = normalized.rstrip("/")
    for label, rx in cfg.GUARDED_SHAPES:
        if any(rx.search(base + tail) for tail in PARENT_TAILS):
            return f"a folder that holds {label}"
    for label, root in roots:
        if root.startswith(base + "/") and root[len(base) + 1:].count("/") <= 1:
            return f"a folder that holds {label}"
    return None


def word_reasons(word, here, roots):
    """Guarded places one word names: the word as a path (relative words against the part's working folder),
    every match when it holds a wildcard, and a parent of a guarded folder."""
    found = []
    candidates = [cfg.norm_path(word, here)]
    if GLOB_CHARS.search(word):
        import glob
        raw = cfg.expand(word.strip().strip("'\""))
        if here and not os.path.isabs(raw):
            raw = os.path.join(here, raw)
        try:
            candidates += [cfg.norm_path(m) for m in glob.glob(raw)[:5000]]
        except (OSError, ValueError, re.error):
            pass
    for n in candidates:
        reason = cfg.guarded_reason(n, roots) or holds_guarded(n, roots)
        if reason:
            found.append(reason)
    return found


def named_guarded_paths(command, cwd, roots):
    """Every guarded place the command names, found two ways: each word normalized against the part's working
    folder (folds '..', env vars, Git Bash drives, wildcards), and the whole command scanned for the guarded
    shapes."""
    found = []
    for part, here in parts_with_cwd(command, cwd):
        for w in words(part):
            # --data=<path> and -Path:<path> carry the path after the = or the colon.
            pieces = [m.group(1) for m in re.finditer(r"^-[\w-]+[=:](.+)$", w)]
            if not w.startswith("-"):
                pieces.append(w)
            for piece in pieces:
                found.extend(word_reasons(piece, here, roots))
    flat = cfg.expand(command).replace("\\ ", " ").replace("\\", "/").replace("\"", "").replace("'", "")
    flat = re.sub(r"/+", "/", flat).lower()
    for label, rx in cfg.GUARDED_SHAPES:
        if rx.search(flat):
            found.append(label)
    for label, root in roots:
        if root and root in flat:
            found.append(label)
    return sorted(set(found))


# --------------------------------------------------------------------------------------------- checks

def check_file_tool(tool_input, cwd, roots):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return
    reason = cfg.guarded_reason(cfg.norm_path(path, cwd), roots)
    if reason:
        refuse(f"refused to change {path}, because it is in {reason}.")


def check_shell(command, cwd, roots):
    if not command.strip():
        return
    named = named_guarded_paths(command, cwd, roots)
    walked = [(part, here, cfg.guarded_reason(cfg.norm_path(here), roots) if here else None)
              for part, here in parts_with_cwd(command, cwd)]
    cwd_reason = next((r for _, _, r in walked if r), None)
    cfg.log("data guard", f"cwd={cwd} command={command!r} named={named} working-folder={cwd_reason}")
    if not named and not cwd_reason:
        return
    where = ", ".join(named) if named else f"{cwd_reason} (the working folder)"
    parts, flags = split_command(command)
    if "subst" in flags:
        refuse(f"refused a command that names {where} and runs a command inside it ($(...), backticks or <(...)), "
               "which the guard can't check.")
    for part, here, _ in walked:
        why = part_is_read_only(part, here, roots)
        if why:
            refuse(f"refused a command that names {where}: in the part `{part}`, {why}. "
                   "Commands that name these folders may only read them.")
    # Inside a guarded folder, a tool's default output lands there too, so only the plain commands pass,
    # whether or not the command also names a guarded path.
    for part, _, reason in walked:
        name, _ = program_and_args(words(part))
        if reason and name not in READ_ONLY_PLAIN and name not in CD_COMMANDS:
            refuse(f"refused `{part}`: the working folder is in {reason}, and the tool's default output "
                   "would land there. Run it from your project folder instead.")


def main():
    try:
        data = cfg.read_hook_input()
        tool = data.get("tool_name") or ""
        tool_input = data.get("tool_input") or {}
        cwd = data.get("cwd") or os.getcwd()
        settings, _, _ = cfg.load_settings(cwd)
        roots = cfg.guarded_roots(settings, cwd)
        if tool in FILE_TOOLS:
            check_file_tool(tool_input, cwd, roots)
        elif tool in SHELL_TOOLS:
            check_shell(str(tool_input.get("command") or ""), cwd, roots)
    except SystemExit:
        raise
    except Exception as e:  # fail closed: a guard that can't read the call refuses it
        sys.stderr.write(f"starfield-agent guard: could not check this call ({type(e).__name__}: {e}), so it "
                         "was refused. Please report this at https://github.com/taosecurity/starfield-agent/issues "
                         "with the command; to work without the guard meanwhile, run /plugin and disable "
                         "starfield-agent.\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
