"""Start sf-papyrus-ref's MCP server for the starfield-agent plugin, or a help-only server when it is missing.

Claude Code starts this file from the plugin's .mcp.json. It looks for sf-papyrus-ref in this order and uses the
first one found:

1. --papyrus-ref <folder> on the command line.
2. The papyrus_ref setting, read the same way the hooks read it (hooks/sfmod_config.py): the SF_PAPYRUS_REF
   environment variable, the plugin option (CLAUDE_PLUGIN_OPTION_PAPYRUS_REF), the project's
   .claude/starfield-agent.json, then the user's starfield-agent.json.
3. sf_papyrus_ref.py, or the sf-papyrus-ref command, on PATH.

Found: it runs `python -I <folder>/sf_papyrus_ref.py mcp --quiet` with stdin and stdout passed straight through and
returns that exit code. Not found: it serves a small MCP server (one JSON-RPC message per line on stdin and stdout)
with one tool, papyrus_setup_help, which says how to install sf-papyrus-ref and where to name its folder.

It never opens a network connection. Messages go to stderr (Claude Code keeps them in its MCP log);
--log <file> also writes them to a file.

Usage: python -I papyrus_ref_launcher.py [--papyrus-ref <folder>] [--log <file>] [--find]
--find prints what it would start, then exits (0 found, 1 not found), without serving anything.
Standard library only.
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import sfmod_config as cfg  # noqa: E402

VERSION = "0.1.0"
DOWNLOAD = "https://github.com/taosecurity/sf-papyrus-ref/releases"
MCP_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

_log_file = None


def say(text):
    line = f"papyrus-ref launcher: {text}"
    print(line, file=sys.stderr, flush=True)
    if _log_file:
        _log_file.write(line + "\n")
        _log_file.flush()


def _usable(value):
    """A folder value counts only when it is non-empty and not an unsubstituted ${...} placeholder."""
    return isinstance(value, str) and value.strip() and not value.strip().startswith("${")


def find_tool(cli_folder=None, cwd=None):
    """Return (command list or None, list of notes saying what was tried)."""
    notes = []
    candidates = []
    if _usable(cli_folder):
        candidates.append(("--papyrus-ref", cli_folder))
    settings, sources, problems = cfg.load_settings(cwd)
    notes.extend(problems)
    if _usable(settings.get("papyrus_ref")):
        candidates.append((sources.get("papyrus_ref", "settings"), settings["papyrus_ref"]))
    for where, folder in candidates:
        folder = cfg.expand(folder.strip().strip("'\""))
        script = folder if folder.lower().endswith(".py") and os.path.isfile(folder) else \
            os.path.join(folder, "sf_papyrus_ref.py")
        if os.path.isfile(script):
            notes.append(f"found {script} (from {where})")
            return [sys.executable, "-I", script, "mcp", "--quiet"], notes
        notes.append(f"{where} names {folder}, but it holds no sf_papyrus_ref.py")
    found = cfg.safe_which(["sf_papyrus_ref.py"], cwd)
    if found:
        notes.append(f"found {found} on PATH")
        return [sys.executable, "-I", found, "mcp", "--quiet"], notes
    found = cfg.safe_which(["sf-papyrus-ref"], cwd)
    if found:
        notes.append(f"found the sf-papyrus-ref command at {found} on PATH")
        return [found, "mcp", "--quiet"], notes
    notes.append("sf_papyrus_ref.py is not on PATH")
    return None, notes


# --------------------------------------------------------------------------------------------- the help-only stub

HELP_TOOL = {
    "name": "papyrus_setup_help",
    "description": "sf-papyrus-ref (the offline Starfield Papyrus reference) is not installed or not found. "
                   "Call this to learn how to install it and where to name its folder. Read-only.",
    "inputSchema": {"type": "object", "properties": {}},
}


def help_text(notes):
    lines = [
        "sf-papyrus-ref was not found, so the Papyrus lookup tools (papyrus_lookup, papyrus_script, "
        "papyrus_list_flag, papyrus_check) are not available.",
        "",
        "To add them:",
        f"1. Download the sf-papyrus-ref release zip from {DOWNLOAD} and unzip it to a folder of your choice.",
        "2. Name that folder in one of these places (the first one found wins):",
        "   - the plugin's 'sf-papyrus-ref folder' option (/plugin, then starfield-agent, then configure);",
        "   - the SF_PAPYRUS_REF environment variable;",
        "   - \"papyrus_ref\" in the project's .claude/starfield-agent.json or in the user's "
        "starfield-agent.json (the setup skill writes this file).",
        "   Or put the folder on PATH.",
        "3. Restart Claude Code (or run /mcp and reconnect papyrus-ref).",
        "",
        "What the launcher tried:",
    ]
    lines += [f"- {n}" for n in notes]
    return "\n".join(lines)


def reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(method, msg_id, params, notes):
    if method == "initialize":
        asked = params.get("protocolVersion")
        reply(msg_id, {"protocolVersion": asked if asked in MCP_VERSIONS else MCP_VERSIONS[0],
                       "capabilities": {"tools": {}},
                       "serverInfo": {"name": "papyrus-ref-setup-help", "version": VERSION},
                       "instructions": "sf-papyrus-ref is not installed. Call papyrus_setup_help to learn how "
                                       "to add the offline Papyrus reference."})
    elif method == "ping":
        reply(msg_id, {})
    elif method == "tools/list":
        reply(msg_id, {"tools": [HELP_TOOL]})
    elif method == "tools/call":
        name = params.get("name")
        if name != HELP_TOOL["name"]:
            text = f"Unknown tool {name}: sf-papyrus-ref is not installed. " + help_text(notes)
            reply(msg_id, {"content": [{"type": "text", "text": text}], "isError": True})
            return
        reply(msg_id, {"content": [{"type": "text", "text": help_text(notes)}], "isError": False})
    else:
        reply(msg_id, error={"code": -32601, "message": f"Method not found: {method}"})


def serve_stub(notes):
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", newline="\n")
    say("serving the help-only stub (one tool: papyrus_setup_help)")
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            reply(None, error={"code": -32700, "message": "Parse error"})
            continue
        if not isinstance(msg, dict):
            reply(None, error={"code": -32600, "message": "Invalid request"})
            continue
        method, msg_id, params = msg.get("method"), msg.get("id"), msg.get("params")
        if msg_id is None:
            continue  # a notification, such as notifications/initialized
        if params is None:
            params = {}
        if not isinstance(params, dict):
            reply(msg_id, error={"code": -32602, "message": "params must be an object"})
            continue
        try:
            handle(method, msg_id, params, notes)
        except Exception as e:  # one bad request must never stop the server
            say(f"request {method} failed: {e!r}")
            reply(msg_id, error={"code": -32603, "message": f"Internal error: {e}"})
    return 0


def main(argv=None):
    global _log_file
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--papyrus-ref", help="the folder that holds sf_papyrus_ref.py")
    ap.add_argument("--log", help="also write the launcher's messages to this file")
    ap.add_argument("--find", action="store_true", help="print what would start, then exit (0 found, 1 not)")
    args = ap.parse_args(argv)
    if args.log:
        try:
            _log_file = open(args.log, "a", encoding="utf-8")
        except OSError as e:
            print(f"papyrus-ref launcher: could not open the log file {args.log}: {e}", file=sys.stderr)

    cmd, notes = find_tool(args.papyrus_ref)
    for n in notes:
        say(n)
    if args.find:
        print(" ".join(cmd) if cmd else "not found")
        return 0 if cmd else 1
    if not cmd:
        return serve_stub(notes)
    say("starting " + " ".join(cmd))
    try:
        # stdin, stdout and stderr are inherited, so MCP messages pass straight through.
        return subprocess.call(cmd)
    except OSError as e:
        say(f"could not start sf-papyrus-ref ({e}); serving the help-only stub instead")
        return serve_stub(notes + [f"starting {' '.join(cmd)} failed: {e}"])
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
