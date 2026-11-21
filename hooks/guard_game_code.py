"""starfield-modding game-code guard: keep Bethesda's files and code out of commits, pushes, releases and gists.

A Claude Code PreToolUse hook (DESIGN.md section 4.2) for Bash and PowerShell. It acts only on `git add`,
`git commit`, `git push`, `gh release create`, `gh release upload` and `gh gist create`, lists the files that would
go up, and then:

- refuses (exit 2, reason on stderr) official plugins and archives by name, the game's and the Creation Kit's
  executables, the Creation Kit's script-source zip, Ghidra and IDA databases, saves, `.psc` files in the Creation
  Kit's `Scripts/Source/Base` folder, and `.psc` files whose name sf-papyrus-ref knows as an official script;
- asks the user (permissionDecision "ask") about a file whose first lines look like decompiler output, because
  that test is a guess and the user's own file may trip it;
- lets everything else through (exit 0).

It only reads: `git diff`, `git log`, `git cat-file` and `git add --dry-run`. It never runs the command itself and
never changes the repo. Standard library only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfmod_config as cfg  # noqa: E402
from guard_game import program_and_args, split_command, words  # noqa: E402

OFFICIAL_PLUGINS = {"starfield.esm", "constellation.esm", "oldmars.esm", "shatteredspace.esm",
                    "blueprintships-starfield.esm"}
OFFICIAL_PLUGIN_RX = re.compile(r"^sfbgs[0-9a-z]*\.es[mlp]$")
OFFICIAL_ARCHIVE_RX = re.compile(r"^(starfield|constellation|oldmars|shatteredspace|blueprintships-starfield|"
                                 r"sfbgs[0-9a-z]*) - .*\.ba2$")
OFFICIAL_FILES = {"starfield.exe": "the game's executable", "creationkit.exe": "the Creation Kit's executable",
                  "contentresources.zip": "the Creation Kit's zip of official script sources"}
DATABASE_SUFFIXES = {".gpr": "a Ghidra project", ".i64": "an IDA database", ".idb": "an IDA database",
                     ".sfs": "a Starfield save"}
TEXT_SUFFIXES = {".psc", ".c", ".cpp", ".cc", ".h", ".hpp", ".txt", ".java", ".pas"}

# Signs of decompiler output in a file's first lines. A guess, so a match asks the user instead of refusing.
BANNER_RX = [
    re.compile(r"decompiled\s+(by|with)\s+champollion", re.I),
    re.compile(r"^\s*(//|;|/\*|#)\s*decompiled\s+(by|with|using)\b", re.I | re.M),
    re.compile(r"hex-rays\s+decompiler", re.I),
    re.compile(r"/\*\s*WARNING:\s*(Could not recover|Globals starting with|Removing unreachable|"
               r"Unknown calling convention)", re.I),
]
GHIDRA_NAMES = re.compile(r"\b(FUN|LAB|DAT)_[0-9a-fA-F]{8,}\b")
GHIDRA_TYPES = re.compile(r"\bundefined[1248]?\b")

HEAD_BYTES = 4096
MAX_CONTENT_READS = 300
MAX_LOOKUPS = 40


class Findings:
    def __init__(self):
        self.refused, self.asked, self.notes = [], [], []

    def add(self, verdict, item, reason):
        (self.refused if verdict == "refuse" else self.asked).append(f"{item}: {reason}")


# --------------------------------------------------------------------------------------------- the checks

class PapyrusNames:
    """Asks sf-papyrus-ref whether a script name is official (`script <name>`: exit 0 found, 1 not found)."""

    def __init__(self, settings):
        self.cmd = None
        folder = settings.get("papyrus_ref")
        if isinstance(folder, str) and folder:
            script = os.path.join(cfg.expand(folder), "sf_papyrus_ref.py")
            if os.path.isfile(script):
                self.cmd = [sys.executable, "-I", script]
        if not self.cmd:
            found = shutil.which("sf_papyrus_ref.py")
            if found:
                self.cmd = [sys.executable, "-I", found]
            else:
                found = shutil.which("sf-papyrus-ref")
                if found:
                    self.cmd = [found]
        self.cache, self.lookups, self.missing_used = {}, 0, False

    def is_official(self, name):
        if not self.cmd:
            self.missing_used = True
            return None
        key = name.lower()
        if key in self.cache:
            return self.cache[key]
        if self.lookups >= MAX_LOOKUPS:
            return None
        self.lookups += 1
        try:
            proc = subprocess.run(self.cmd + ["script", name], capture_output=True, timeout=20)
            result = True if proc.returncode == 0 else False if proc.returncode == 1 else None
        except (OSError, subprocess.SubprocessError):
            result = None
        self.cache[key] = result
        return result


def check_name(path, findings, names, shown=None):
    """Checks that need only the file's path. Returns True when it was refused."""
    shown = shown or path
    p = path.replace("\\", "/")
    base = p.rsplit("/", 1)[-1].lower()
    lower = p.lower()
    suffix = os.path.splitext(base)[1]
    if base in OFFICIAL_PLUGINS or OFFICIAL_PLUGIN_RX.match(base):
        findings.add("refuse", shown, "an official Starfield plugin")
    elif OFFICIAL_ARCHIVE_RX.match(base):
        findings.add("refuse", shown, "an official Starfield archive")
    elif base in OFFICIAL_FILES:
        findings.add("refuse", shown, OFFICIAL_FILES[base])
    elif suffix in DATABASE_SUFFIXES:
        findings.add("refuse", shown, DATABASE_SUFFIXES[suffix])
    elif any(part.endswith(".rep") for part in lower.split("/")[:-1]):
        findings.add("refuse", shown, "part of a Ghidra project (.rep folder)")
    elif suffix == ".psc" and "scripts/source/base/" in "/" + lower:
        findings.add("refuse", shown, "an official script source (the Creation Kit's Scripts/Source/Base folder)")
    elif suffix == ".psc" and names.is_official(os.path.splitext(p.rsplit("/", 1)[-1])[0]):
        findings.add("refuse", shown, "has the name of an official script (sf-papyrus-ref knows it); if you "
                     "wrote it yourself, give it your mod's prefix")
    else:
        return False
    return True


def check_head(head, findings, shown):
    text = head.decode("utf-8", errors="replace")
    for rx in BANNER_RX:
        if rx.search(text):
            findings.add("ask", shown, "its first lines look like decompiler output")
            return
    if len(GHIDRA_NAMES.findall(text)) >= 2 and GHIDRA_TYPES.search(text):
        findings.add("ask", shown, "its first lines look like Ghidra decompiler output (FUN_/DAT_ names)")


def wants_content(path):
    return os.path.splitext(path.lower())[1] in TEXT_SUFFIXES


def check_local_file(path, findings, names, shown=None, reads=None):
    """A file on disk: name checks, then a zip's members, then the first lines of a text file."""
    shown = shown or path
    if check_name(path, findings, names, shown):
        return
    if path.lower().endswith(".zip") and os.path.isfile(path):
        try:
            with zipfile.ZipFile(path) as z:
                for info in z.infolist()[:5000]:
                    member = f"{shown} -> {info.filename}"
                    if check_name(info.filename, findings, names, member) or info.is_dir():
                        continue
                    if wants_content(info.filename) and reads[0] < MAX_CONTENT_READS:
                        reads[0] += 1
                        with z.open(info) as f:
                            check_head(f.read(HEAD_BYTES), findings, member)
        except (OSError, zipfile.BadZipFile) as e:
            findings.notes.append(f"could not read {shown} as a zip ({e})")
        return
    if wants_content(path) and os.path.isfile(path) and reads[0] < MAX_CONTENT_READS:
        reads[0] += 1
        try:
            with open(path, "rb") as f:
                check_head(f.read(HEAD_BYTES), findings, shown)
        except OSError:
            pass


# --------------------------------------------------------------------------------------------- git

def git(repo, *args):
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip() or f"git {args[0]} failed")
    return proc.stdout


def git_blob_head(repo, spec):
    try:
        proc = subprocess.run(["git", "-C", repo, "cat-file", "-p", spec], capture_output=True, timeout=30)
        return proc.stdout[:HEAD_BYTES] if proc.returncode == 0 else b""
    except (OSError, subprocess.SubprocessError):
        return b""


def zsplit(raw):
    return [x for x in raw.decode("utf-8", errors="replace").split("\0") if x]


COMMIT_VALUE_OPTS = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message",
                     "--author", "--date", "--fixup", "--squash", "-t", "--template", "--cleanup", "--trailer"}
PUSH_VALUE_OPTS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def positional(args, value_opts):
    out, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            out.extend(args[i + 1:])
            break
        if a.startswith("-"):
            if a in value_opts:
                i += 1
        else:
            out.append(a)
        i += 1
    return out


def files_git_add(repo, args):
    flags = [a for a in args if a in ("-A", "--all", "-u", "--update", "-f", "--force", "--no-ignore-removal")]
    specs = positional(args, {"--chmod", "--pathspec-from-file"})
    try:
        out = git(repo, "add", "--dry-run", *flags, "--", *specs).decode("utf-8", errors="replace")
        return [m.group(1) for m in re.finditer(r"^add '(.+)'$", out, re.M)]
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return specs


def files_git_commit(repo, args):
    files = zsplit(git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z"))
    short = [a for a in args if re.match(r"^-[A-Za-z]+$", a) and a not in COMMIT_VALUE_OPTS]
    if "--all" in args or any("a" in a[1:] for a in short):
        files += zsplit(git(repo, "diff", "--name-only", "--diff-filter=ACMRT", "-z"))
    specs = positional(args, COMMIT_VALUE_OPTS)
    if specs:
        files += zsplit(git(repo, "diff", "HEAD", "--name-only", "--diff-filter=ACMRT", "-z", "--", *specs))
    return sorted(set(files))


def revs_git_push(args):
    if "--delete" in args or "-d" in args:
        return []
    revs = []
    if "--all" in args or "--branches" in args or "--mirror" in args:
        revs.append("--branches")
    if "--tags" in args or "--follow-tags" in args or "--mirror" in args:
        revs.append("--tags")
    for spec in positional(args, PUSH_VALUE_OPTS)[1:]:
        src = spec.lstrip("+").split(":", 1)[0]
        if src:
            revs.append(src)
    return revs or ["HEAD"]


def commits_git_push(repo, args):
    """(commit, path) for every file added or changed in a commit the push would send."""
    revs = revs_git_push(args)
    if not revs:
        return []
    out = git(repo, "log", "--format=%x01%H", "--name-only", "--diff-filter=ACMRT", "-z", *revs, "--not",
              "--remotes").decode("utf-8", errors="replace")
    pairs, commit = [], None
    for item in out.replace("\n", "\0").split("\0"):
        item = item.strip()
        if not item:
            continue
        if item.startswith("\x01"):
            commit = item[1:]
        elif commit:
            pairs.append((commit, item))
    return pairs


# --------------------------------------------------------------------------------------------- gh

GH_VALUE_OPTS = {"-R", "--repo", "-t", "--title", "-n", "--notes", "-F", "--notes-file", "--target",
                 "--discussion-category", "--notes-start-tag", "-d", "--desc", "-f", "--filename"}


def gh_files(sub, args):
    pos = positional(args, GH_VALUE_OPTS)
    if sub[0] == "release":
        pos = pos[2:]          # "create|upload" and the tag
    else:
        pos = pos[1:]          # "create"
    return [p.split("#", 1)[0] for p in pos if p != "-"]


# --------------------------------------------------------------------------------------------- main

def git_global(args):
    """Split git's global options from the subcommand; returns (repo override or None, subcommand, rest)."""
    repo, i = None, 0
    while i < len(args):
        a = args[i]
        if a == "-C" and i + 1 < len(args):
            repo = args[i + 1] if repo is None or os.path.isabs(args[i + 1]) else os.path.join(repo, args[i + 1])
            i += 2
        elif a in ("-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(args):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            return repo, a, args[i + 1:]
    return repo, "", []


def check_command(command, cwd, settings, findings):
    names = PapyrusNames(settings)
    reads = [0]
    parts, _ = split_command(command)
    here = cwd
    for part in parts:
        ws = words(part)
        name, args = program_and_args(ws)
        if name in ("cd", "set-location", "sl", "pushd", "chdir") and args:
            target = cfg.expand(args[-1])
            here = target if os.path.isabs(target) else os.path.join(here, target)
            continue
        if name == "git":
            override, sub, rest = git_global(args)
            repo = here if override is None else (override if os.path.isabs(override)
                                                  else os.path.join(here, override))
            try:
                if sub == "add":
                    for f in files_git_add(repo, rest):
                        check_local_file(os.path.join(repo, f), findings, names, f, reads)
                elif sub == "commit":
                    for f in files_git_commit(repo, rest):
                        if not check_name(f, findings, names) and wants_content(f) and reads[0] < MAX_CONTENT_READS:
                            reads[0] += 1
                            check_head(git_blob_head(repo, ":" + f), findings, f)
                elif sub == "push":
                    seen = set()
                    for commit, f in commits_git_push(repo, rest):
                        if check_name(f, findings, names, f"{f} (in commit {commit[:9]})"):
                            continue
                        if f not in seen and wants_content(f) and reads[0] < MAX_CONTENT_READS:
                            seen.add(f)
                            reads[0] += 1
                            check_head(git_blob_head(repo, f"{commit}:{f}"), findings, f"{f} (in commit {commit[:9]})")
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                findings.notes.append(f"could not list the files for `git {sub}` ({e}); nothing was checked")
        elif name == "gh" and len(args) >= 2 and (args[0], args[1]) in (
                ("release", "create"), ("release", "upload"), ("gist", "create")):
            for f in gh_files((args[0], args[1]), args):
                path = f if os.path.isabs(cfg.expand(f)) else os.path.join(here, cfg.expand(f))
                check_local_file(path, findings, names, f, reads)
    if names.missing_used:
        findings.notes.append("sf-papyrus-ref is not installed, so .psc files were checked by folder only")


RELEVANT = re.compile(r"\bgit\b[^;&|\n]*\b(add|commit|push)\b|\bgh\b[^;&|\n]*\b(release|gist)\b", re.I)


def main():
    try:
        data = cfg.read_hook_input()
        if data.get("tool_name") not in ("Bash", "PowerShell"):
            sys.exit(0)
        command = str((data.get("tool_input") or {}).get("command") or "")
        if not RELEVANT.search(command):
            sys.exit(0)
        cwd = data.get("cwd") or os.getcwd()
        settings, _, _ = cfg.load_settings(cwd)
        findings = Findings()
        check_command(command, cwd, settings, findings)
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        sys.stderr.write(f"starfield-modding game-code guard: could not check this command ({type(e).__name__}: "
                         f"{e}), so it was refused. Please report it at "
                         "https://github.com/taosecurity/starfield-modding/issues.\n")
        sys.exit(2)

    notes = ("\nNotes: " + "; ".join(findings.notes)) if findings.notes else ""
    if findings.refused:
        sys.stderr.write("starfield-modding game-code guard: refused, because this would share Bethesda's files "
                         "or code:\n- " + "\n- ".join(findings.refused[:20])
                         + ("\n- ..." if len(findings.refused) > 20 else "")
                         + "\nTake these out (git rm --cached, .gitignore, or leave them out of the release), "
                         "then try again. Never bypass this check." + notes + "\n")
        sys.exit(2)
    if findings.asked:
        reason = ("starfield-modding game-code guard: please confirm. These files may be decompiled game code, "
                  "which must never be shared:\n- " + "\n- ".join(findings.asked[:20])
                  + "\nAllow only if you wrote them yourself." + notes)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": reason}}))
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
