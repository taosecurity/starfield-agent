"""Shared settings and path helpers for the starfield-agent hooks (DESIGN.md section 6).

Each key is read from the first place that has it:

1. Environment variables: SFMOD_GAME_DIR, SFMOD_SAVES_DIR, SFMOD_EXTRA_GUARDED (paths separated by ';'),
   SF_PAPYRUS_REF. Then the plugin's own options (Claude Code exports them to hooks as
   CLAUDE_PLUGIN_OPTION_GAME_DIR, CLAUDE_PLUGIN_OPTION_SAVES_DIR, CLAUDE_PLUGIN_OPTION_PAPYRUS_REF).
2. The project's .claude/starfield-agent.json (the project is CLAUDE_PROJECT_DIR, else the hook's cwd). It is
   never trusted for papyrus_ref, which names a program to run (a downloaded project could ship its own file).
3. The user's starfield-agent.json: %APPDATA%\\starfield-agent\\ on Windows, ~/.config/starfield-agent/ elsewhere
   (SFMOD_USER_CONFIG names another file, which the tests use).
   Until 0.2.0 the plugin was called starfield-modding: when a starfield-agent.json file is missing, the old
   starfield-modding.json in the same place is read instead, with the same rules.
4. Detection: the guarded folders below match any Steam library, Game Pass install, OneDrive Documents and Proton
   prefix by their shape, so no install has to be found first.

Keys: game_dir, saves_dir, extra_guarded (list), papyrus_ref, mod_manager ({"kind", "path"}).
The folder keys (game_dir, saves_dir, extra_guarded) are guarded from every layer together, so no layer can take a
folder away that another guards. Empty values and unfilled ${...} placeholders count as not set.
SFMOD_HOOK_LOG names a file that both guards append their reads and decisions to (troubleshooting; off by default).
Standard library only.
"""

import json
import ntpath
import os
import posixpath
import re
import sys

KEYS = ("game_dir", "saves_dir", "extra_guarded", "papyrus_ref", "mod_manager")

ENV_KEYS = {
    "game_dir": ("SFMOD_GAME_DIR", "CLAUDE_PLUGIN_OPTION_GAME_DIR"),
    "saves_dir": ("SFMOD_SAVES_DIR", "CLAUDE_PLUGIN_OPTION_SAVES_DIR"),
    "extra_guarded": ("SFMOD_EXTRA_GUARDED", "CLAUDE_PLUGIN_OPTION_EXTRA_GUARDED"),
    "papyrus_ref": ("SF_PAPYRUS_REF", "CLAUDE_PLUGIN_OPTION_PAPYRUS_REF"),
}

# Guarded by shape, wherever the install is. Each entry is (label, regex on a normalized path).
# Normalized paths are lower case with forward slashes (see norm_path).
# The end test (?![\w.-]) also works inside a whole command line, where a quote or a space follows the path.
_END = r"(?![\w.-])"
GUARDED_SHAPES = [
    ("the game's Data folder (Steam)", re.compile(r"/steamapps/common/starfield/data" + _END)),
    ("the game's Data folder (Game Pass)", re.compile(r"/xboxgames/starfield/content/data" + _END)),
    ("the Starfield saves folder", re.compile(r"/my games/starfield/saves" + _END)),
    ("the Game Pass save container", re.compile(r"/packages/bethesdasoftworks\.projectgold_")),
    ("the game's Plugins.txt", re.compile(r"/appdata/local/starfield/plugins\.txt" + _END)),
    ("the game's ContentCatalog.txt", re.compile(r"/appdata/local/starfield/contentcatalog\.txt" + _END)),
]


NAME = "starfield-agent"
OLD_NAME = "starfield-modding"   # the plugin's name before 0.2.0; its settings files are still read


def _with_fallback(new_path, old_path):
    """The new settings file when it exists, else the 0.1.0 file when that exists, else the new path."""
    if not os.path.exists(new_path) and os.path.exists(old_path):
        return old_path
    return new_path


def _user_config_path():
    override = os.environ.get("SFMOD_USER_CONFIG")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return _with_fallback(os.path.join(base, NAME, NAME + ".json"), os.path.join(base, OLD_NAME, OLD_NAME + ".json"))


def project_config_path(cwd=None):
    folder = os.path.join(project_dir(cwd), ".claude")
    return _with_fallback(os.path.join(folder, NAME + ".json"), os.path.join(folder, OLD_NAME + ".json"))


def _read_json(path, problems):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        problems.append(f"could not read settings file {path}: {e}")
        return {}
    if not isinstance(data, dict):
        problems.append(f"settings file {path} is not a JSON object; ignored")
        return {}
    return data


def project_dir(cwd=None):
    return os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()


# Keys that name a program to run. A cloned project could ship its own settings file, so these are read only from
# the environment, the plugin's options and the user's own file, never from the project's file.
UNTRUSTED_IN_PROJECT = ("papyrus_ref",)
# Keys that add guarded folders. Every layer's values are guarded together (settings["guard_paths"]), so a project
# file can add folders but never take away a folder the user's file or the environment guards.
GUARD_KEYS = ("game_dir", "saves_dir", "extra_guarded")


def is_unset(value):
    """Empty values and unfilled placeholders such as ${user_config.papyrus_ref} count as not set."""
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        return not v or v.startswith("${")
    return value in ([], {})


def load_settings(cwd=None):
    """Return (settings, sources, problems). sources maps each key to where its value came from.
    settings["guard_paths"] lists (key, path) from every layer, for guarded_roots."""
    problems = []
    project_file = project_config_path(cwd)
    project_label = "project file " + project_file
    layers = [
        (project_label, _read_json(project_file, problems)),
        ("user file " + _user_config_path(), _read_json(_user_config_path(), problems)),
    ]
    for key in UNTRUSTED_IN_PROJECT:
        if not is_unset(layers[0][1].get(key)):
            problems.append(f"ignored {key} in {project_file}: it names a program to run, so it is read only from "
                            "your own settings file, the plugin options or an environment variable")
    settings, sources, guard_paths = {}, {}, []

    def as_list(key, value):
        if key == "extra_guarded":
            items = value.split(";") if isinstance(value, str) else value if isinstance(value, list) else []
            return [p for p in items if isinstance(p, str) and not is_unset(p)]
        return [value] if isinstance(value, str) and not is_unset(value) else []

    for key in KEYS:
        found = []
        for env_name in ENV_KEYS.get(key, ()):
            value = os.environ.get(env_name, "")
            if not is_unset(value):
                found.append(("environment variable " + env_name, value.strip()))
        for label, data in layers:
            if label == project_label and key in UNTRUSTED_IN_PROJECT:
                continue
            value = data.get(key)
            if not is_unset(value):
                found.append((label, value))
        if not found:
            continue
        label, value = found[0]
        settings[key] = as_list(key, value) if key == "extra_guarded" else value
        sources[key] = label
        if key in GUARD_KEYS:
            for _, v in found:
                guard_paths.extend((key, p) for p in as_list(key, v))
    settings["guard_paths"] = guard_paths
    return settings, sources, problems


def safe_which(names, cwd=None):
    """Find a program on PATH like shutil.which, but never in the current folder (Windows' shutil.which looks
    there first), in a relative PATH entry or inside the project, so a cloned repo can't plant one."""
    blocked = [p for p in (cwd, os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR")) if p]
    blocked = [os.path.normcase(os.path.abspath(p)).rstrip("\\/") for p in blocked]
    exts = [""]
    if os.name == "nt":
        exts = [""] + [e for e in (os.environ.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD").split(";") if e]
    for folder in (os.environ.get("PATH") or "").split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder or not os.path.isabs(folder):
            continue
        normal = os.path.normcase(os.path.abspath(folder)).rstrip("\\/")
        if any(normal == b or normal.startswith(b + os.sep) for b in blocked):
            continue
        for name in names:
            for ext in exts:
                candidate = os.path.join(folder, name + ext)
                if os.path.isfile(candidate) and (os.name == "nt" or os.access(candidate, os.X_OK)
                                                  or candidate.endswith(".py")):
                    return candidate
    return None


def log(event, detail):
    """Append one line to the troubleshooting log named by SFMOD_HOOK_LOG (off when unset)."""
    path = os.environ.get("SFMOD_HOOK_LOG", "").strip()
    if not path:
        return
    try:
        import datetime
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {event}: {detail}\n")
    except OSError:
        pass


_PS_ENV = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)", re.I)
_BRACED_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand(text):
    """Expand ~, %VAR%, $VAR, ${VAR} and PowerShell's $env:VAR."""
    text = _PS_ENV.sub(lambda m: os.environ.get(m.group(1), m.group(0)), text)
    text = _BRACED_ENV.sub(lambda m: os.environ.get(m.group(1), m.group(0)), text)
    text = ntpath.expandvars(text) if os.name == "nt" else posixpath.expandvars(text)
    if text.startswith("~"):
        text = os.path.expanduser(text)
    return text


def norm_path(path, cwd=None):
    """Normalize a path for comparison: env vars expanded, Git Bash and WSL drive forms turned into C:,
    made absolute against cwd, links resolved where the path exists, then '..' folded, forward slashes,
    lower case."""
    p = expand(path.strip().strip("'\""))
    if not p:
        return ""
    m = re.match(r"^/mnt/([a-zA-Z])(/|$)(.*)", p) or re.match(r"^/([a-zA-Z])(/|$)(.*)", p)
    if m:
        p = f"{m.group(1)}:/{m.group(3)}"
    is_abs = bool(re.match(r"^[a-zA-Z]:[\\/]", p)) or p.startswith(("/", "\\"))
    if not is_abs and cwd:
        p = os.path.join(cwd, p)
    try:
        if os.path.exists(p):
            p = os.path.realpath(p)
    except (OSError, ValueError):
        pass
    p = p.replace("\\", "/")
    if p.startswith("//?/"):
        p = p[4:]
    # normpath folds '..' and repeated slashes, and keeps a UNC path's leading '//'.
    return posixpath.normpath(p).lower()


def guarded_roots(settings, cwd=None):
    """Folders and files guarded because the settings name them: list of (label, normalized path)."""
    roots = []
    if "guard_paths" in settings:
        pairs = settings["guard_paths"]
    else:
        pairs = [(k, settings.get(k)) for k in ("game_dir", "saves_dir")]
        pairs += [("extra_guarded", p) for p in settings.get("extra_guarded") or []]
    for key, path in pairs:
        if not isinstance(path, str) or is_unset(path):
            continue
        if key == "game_dir":
            roots.append(("the game's Data folder (game_dir setting)", norm_path(os.path.join(path, "Data"), cwd)))
        elif key == "saves_dir":
            roots.append(("the saves folder (saves_dir setting)", norm_path(path, cwd)))
        else:
            roots.append(("a folder in the extra_guarded setting", norm_path(path, cwd)))
    seen, out = set(), []
    for label, root in roots:
        if root and root not in seen:
            seen.add(root)
            out.append((label, root))
    return out


def guarded_reason(normalized, roots):
    """Return a label when a normalized path is inside a guarded folder or is a guarded file, else None."""
    if not normalized:
        return None
    for label, rx in GUARDED_SHAPES:
        if rx.search(normalized):
            return label
    for label, root in roots:
        if normalized == root or normalized.startswith(root.rstrip("/") + "/"):
            return label
    return None


def read_hook_input():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("hook input is not a JSON object")
    return data
