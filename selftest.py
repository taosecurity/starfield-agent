"""Run every test of the starfield-modding plugin, then `claude plugin validate .`.

The tests are every tests/test_*.py: test_skills.py (the skills), test_guard_game.py (the Data and saves guard)
test_guard_game_code.py (the game-code guard; needs git on PATH) and test_launcher.py (the MCP launcher; its real
sf-papyrus-ref run needs SFMOD_TEST_PAPYRUS_REF or SF_PAPYRUS_REF set to the tool's folder, else it is skipped).

Usage: python -I selftest.py [--no-claude] [--verbose]

--no-claude  skip `claude plugin validate .` (for a machine without Claude Code; the run then says it was skipped)
--verbose    print each test's name

Exit code 0 when everything passed, 1 when a test or the validation failed, 2 when Claude Code wasn't found.
"""

import argparse
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_tests(verbose):
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    return result.wasSuccessful(), result.testsRun


def run_validate():
    claude = shutil.which("claude")
    if not claude:
        print("selftest: Claude Code (`claude`) not found on PATH. Install it, or run with --no-claude.", file=sys.stderr)
        return None
    proc = subprocess.run([claude, "plugin", "validate", "."], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    for stream, text in ((sys.stdout, proc.stdout), (sys.stderr, proc.stderr)):
        text = (text or "").strip()
        if text:
            # The console may not show every character Claude Code prints (check marks); replace those.
            enc = stream.encoding or "utf-8"
            print(text.encode(enc, errors="replace").decode(enc), file=stream)
    return proc.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-claude", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    ok, count = run_tests(args.verbose)
    print(f"selftest: {count} tests, {'OK' if ok else 'FAILED'}")

    if args.no_claude:
        print("selftest: claude plugin validate skipped (--no-claude)")
        valid = True
    else:
        valid = run_validate()
        if valid is None:
            return 2
        print(f"selftest: claude plugin validate {'OK' if valid else 'FAILED'}")

    passed = ok and valid
    print(f"RESULT: {'OK' if passed else 'FAILED'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
