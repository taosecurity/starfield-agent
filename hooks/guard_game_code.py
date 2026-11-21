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

Zips are opened and their members checked, whether they are on disk (git add, gh) or in git (commit, push). When the
files can't be listed or a zip can't be read, it asks instead of letting the command through.

It only reads: `git diff`, `git log`, `git ls-files`, `git for-each-ref`, `git cat-file` and `git add --dry-run`
(push revisions go after --end-of-options, so a refspec can't become a git option). It never runs the command
itself and never changes the repo. Standard library only.
"""

import json
import os
import re
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

    def __init__(self, settings, cwd=None):
        self.cmd = None
        folder = settings.get("papyrus_ref")
        if isinstance(folder, str) and folder:
            script = os.path.join(cfg.expand(folder), "sf_papyrus_ref.py")
            if os.path.isfile(script):
                self.cmd = [sys.executable, "-I", script]
        if not self.cmd:
            found = cfg.safe_which(["sf_papyrus_ref.py"], cwd)
            if found:
                self.cmd = [sys.executable, "-I", found]
            else:
                found = cfg.safe_which(["sf-papyrus-ref"], cwd)
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


def check_zip(source, findings, names, shown, reads):
    """A zip's members (source is a path or a file object): name checks, then the first lines of text members.
    A zip that can't be read is asked about, because its members went unchecked."""
    try:
        with zipfile.ZipFile(source) as z:
            for info in z.infolist()[:5000]:
                member = f"{shown} -> {info.filename}"
                if check_name(info.filename, findings, names, member) or info.is_dir():
                    continue
                if wants_content(info.filename) and reads[0] < MAX_CONTENT_READS:
                    reads[0] += 1
                    with z.open(info) as f:
                        check_head(f.read(HEAD_BYTES), findings, member)
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as e:
        findings.add("ask", shown, f"it could not be read as a zip ({e}), so its contents were not checked")


def check_local_file(path, findings, names, shown=None, reads=None):
    """A file on disk: name checks, then a zip's members, then the first lines of a text file."""
    shown = shown or path
    if check_name(path, findings, names, shown):
        return
    if path.lower().endswith(".zip") and os.path.isfile(path):
        check_zip(path, findings, names, shown, reads)
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


MAX_ZIP_BLOB = 512 * 1024 * 1024


def check_git_zip(repo, spec, findings, names, shown, reads):
    """A zip stored in git (spec such as ':path' or '<commit>:path'): read the blob and check its members."""
    import io
    try:
        size = int(git(repo, "cat-file", "-s", spec).strip() or 0)
        if size > MAX_ZIP_BLOB:
            findings.add("ask", shown, f"a {size // (1024 * 1024)} MB zip, too large for the guard to open")
            return
        check_zip(io.BytesIO(git(repo, "cat-file", "blob", spec)), findings, names, shown, reads)
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as e:
        findings.add("ask", shown, f"the guard could not read this zip from git ({e})")


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
        try:
            files += zsplit(git(repo, "diff", "HEAD", "--name-only", "--diff-filter=ACMRT", "-z", "--", *specs))
        except RuntimeError:
            # No HEAD yet (the first commit): every tracked file the pathspecs name goes in.
            files += zsplit(git(repo, "ls-files", "-z", "--", *specs))
    return sorted(set(files))


def revs_git_push(args):
    """(options, revs) for git log: the commits a push would send. Revs that look like options are refused
    by git log itself, because they come after --end-of-options."""
    if "--delete" in args or "-d" in args:
        return [], []
    opts, revs = [], []
    if "--all" in args or "--branches" in args or "--mirror" in args:
        opts.append("--branches")
    if "--tags" in args or "--follow-tags" in args or "--mirror" in args:
        opts.append("--tags")
    specs = positional(args, PUSH_VALUE_OPTS)[1:]
    i = 0
    while i < len(specs):
        spec = specs[i]
        if spec == "tag" and i + 1 < len(specs):       # git push origin tag v1.0
            revs.append("refs/tags/" + specs[i + 1])
            i += 2
            continue
        src = spec.lstrip("+").split(":", 1)[0]
        if src:
            revs.append(src)
        i += 1
    if not opts and not revs:
        revs = ["HEAD"]
    return opts, revs


def commits_git_push(repo, args):
    """(commit, path) for every file added or changed in a commit the push would send."""
    opts, revs = revs_git_push(args)
    if not opts and not revs:
        return []
    remote_tips = [line.strip() for line in git(repo, "for-each-ref", "--format=%(objectname)", "refs/remotes")
                   .decode("utf-8", errors="replace").splitlines() if line.strip()]
    out = git(repo, "log", "--format=%x01%H", "--name-only", "--diff-filter=ACMRT", "-z", *opts,
              "--end-of-options", *revs, *("^" + t for t in remote_tips), "--").decode("utf-8", errors="replace")
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
    """The files a gh release or gist command would upload. args starts with the subcommand words."""
    pos = positional(args, GH_VALUE_OPTS)
    if sub[0] == "release":
        pos = pos[3:]          # "release", "create|upload" and the tag
    else:
        pos = pos[2:]          # "gist", "create"
    return [p.split("#", 1)[0] for p in pos if p != "-"]


GLOB_CHARS = re.compile(r"[*?\[]")


def expand_files(name, here):
    """A file argument as the shell would expand it: a path, or every match of a wildcard."""
    import glob
    path = cfg.expand(name)
    path = path if os.path.isabs(path) else os.path.join(here, path)
    if GLOB_CHARS.search(name):
        return [(m, os.path.relpath(m, here) if not os.path.isabs(name) else m)
                for m in sorted(glob.glob(path))[:5000]]
    return [(path, name)]


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
    names = PapyrusNames(settings, cwd)
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
                        if check_name(f, findings, names):
                            continue
                        if f.lower().endswith(".zip"):
                            # The staged copy goes in, or the working copy with -a or a pathspec: check both.
                            check_git_zip(repo, ":" + f, findings, names, f, reads)
                            on_disk = os.path.join(repo, f)
                            if os.path.isfile(on_disk):
                                check_zip(on_disk, findings, names, f + " (working copy)", reads)
                        elif wants_content(f) and reads[0] < MAX_CONTENT_READS:
                            reads[0] += 1
                            check_head(git_blob_head(repo, ":" + f), findings, f)
                elif sub == "push":
                    seen = set()
                    for commit, f in commits_git_push(repo, rest):
                        shown = f"{f} (in commit {commit[:9]})"
                        if check_name(f, findings, names, shown):
                            continue
                        if f.lower().endswith(".zip"):
                            check_git_zip(repo, f"{commit}:{f}", findings, names, shown, reads)
                        elif f not in seen and wants_content(f) and reads[0] < MAX_CONTENT_READS:
                            seen.add(f)
                            reads[0] += 1
                            check_head(git_blob_head(repo, f"{commit}:{f}"), findings, shown)
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                # Fail closed: files that can't be listed can't be checked, so the user decides.
                findings.add("ask", f"git {sub}", f"the guard could not list the files it would send ({e}), so "
                             "nothing was checked")
        elif name == "gh" and len(args) >= 2 and (args[0], args[1]) in (
                ("release", "create"), ("release", "upload"), ("gist", "create")):
            for f in gh_files((args[0], args[1]), args):
                for path, shown in expand_files(f, here):
                    check_local_file(path, findings, names, shown, reads)
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
        settings, sources, problems = cfg.load_settings(cwd)
        cfg.log("game-code guard", f"cwd={cwd} command={command!r} papyrus_ref from {sources.get('papyrus_ref')}"
                + (f" problems={problems}" if problems else ""))
        findings = Findings()
        findings.notes.extend(problems)
        check_command(command, cwd, settings, findings)
        cfg.log("game-code guard", f"refused={findings.refused} asked={findings.asked} notes={findings.notes}")
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        cfg.log("game-code guard", f"error {type(e).__name__}: {e}; refused")
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
        reason = ("starfield-modding game-code guard: please confirm. These files may hold decompiled game code or "
                  "could not be checked, and game code must never be shared:\n- " + "\n- ".join(findings.asked[:20])
                  + "\nAllow only if you wrote them yourself." + notes)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": reason}}))
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
