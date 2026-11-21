"""Shared settings and path helpers for the starfield-modding hooks (DESIGN.md section 6).

Each key is read from the first place that has it:

1. Environment variables: SFMOD_GAME_DIR, SFMOD_SAVES_DIR, SFMOD_EXTRA_GUARDED (paths separated by ';'),
   SF_PAPYRUS_REF. Then the plugin's own options (Claude Code exports them to hooks as
   CLAUDE_PLUGIN_OPTION_GAME_DIR, CLAUDE_PLUGIN_OPTION_SAVES_DIR, CLAUDE_PLUGIN_OPTION_PAPYRUS_REF).
2. The project's .claude/starfield-modding.json (the project is CLAUDE_PROJECT_DIR, else the hook's cwd).
3. The user's starfield-modding.json: %APPDATA%\\starfield-modding\\ on Windows, ~/.config/starfield-modding/ elsewhere
   (SFMOD_USER_CONFIG names another file, which the tests use).
4. Detection: the guarded folders below match any Steam library, Game Pass install, OneDrive Documents and Proton
   prefix by their shape, so no install has to be found first.

Keys: game_dir, saves_dir, extra_guarded (list), papyrus_ref, mod_manager ({"kind", "path"}).
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


def _user_config_path():
    override = os.environ.get("SFMOD_USER_CONFIG")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "starfield-modding", "starfield-modding.json")
    return os.path.join(os.path.expanduser("~"), ".config", "starfield-modding", "starfield-modding.json")


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


def load_settings(cwd=None):
    """Return (settings, sources, problems). sources maps each key to where its value came from."""
    problems = []
    project_file = os.path.join(project_dir(cwd), ".claude", "starfield-modding.json")
    layers = [
        ("project file " + project_file, _read_json(project_file, problems)),
        ("user file " + _user_config_path(), _read_json(_user_config_path(), problems)),
    ]
    settings, sources = {}, {}
    for key in KEYS:
        for env_name in ENV_KEYS.get(key, ()):
            value = os.environ.get(env_name, "").strip()
            if value:
                settings[key] = [p for p in value.split(";") if p.strip()] if key == "extra_guarded" else value
                sources[key] = "environment variable " + env_name
                break
        if key in settings:
            continue
        for label, data in layers:
            value = data.get(key)
            if value in (None, "", []):
                continue
            if key == "extra_guarded" and isinstance(value, str):
                value = [value]
            settings[key] = value
            sources[key] = label
            break
    return settings, sources, problems


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
    game = settings.get("game_dir")
    if isinstance(game, str) and game:
        roots.append(("the game's Data folder (game_dir setting)", norm_path(os.path.join(game, "Data"), cwd)))
    saves = settings.get("saves_dir")
    if isinstance(saves, str) and saves:
        roots.append(("the saves folder (saves_dir setting)", norm_path(saves, cwd)))
    for extra in settings.get("extra_guarded") or []:
        if isinstance(extra, str) and extra.strip():
            roots.append(("a folder in the extra_guarded setting", norm_path(extra, cwd)))
    return [(label, root) for label, root in roots if root]


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
