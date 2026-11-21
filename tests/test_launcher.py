"""Tests for mcp/papyrus_ref_launcher.py (DESIGN.md section 8.1).

1. With no sf-papyrus-ref anywhere, the help-only stub answers initialize, tools/list (papyrus_setup_help),
   tools/call and ping, ignores notifications and survives bad lines.
2. With a fake sf_papyrus_ref.py that echoes each line, messages pass straight through, from the setting, the
   plugin option, --papyrus-ref and PATH.
3. One real run against an installed sf-papyrus-ref: the folder named by SFMOD_TEST_PAPYRUS_REF or SF_PAPYRUS_REF.
   Skipped when neither names a folder that holds sf_papyrus_ref.py.

Run: python -I tests/test_launcher.py   (or through selftest.py)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "mcp" / "papyrus_ref_launcher.py"

FAKE_TOOL = (
    "import sys\n"
    "assert sys.argv[1:] == ['mcp', '--quiet'], sys.argv\n"
    "for line in sys.stdin:\n"
    "    sys.stdout.write('echo:' + line)\n"
    "    sys.stdout.flush()\n"
)

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
CALL = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "papyrus_setup_help", "arguments": {}}}
PING = {"jsonrpc": "2.0", "id": 4, "method": "ping"}


class LauncherCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.project = self.base / "project"
        self.empty_path = self.base / "emptybin"
        for d in (self.project, self.empty_path):
            d.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("SFMOD_", "SF_PAPYRUS", "CLAUDE_PLUGIN_OPTION_", "CLAUDE_PROJECT_DIR"))}
        env["PATH"] = str(self.empty_path)
        env["SFMOD_USER_CONFIG"] = str(self.base / "no-user-config.json")
        env["CLAUDE_PROJECT_DIR"] = str(self.project)
        env.update(extra)
        return env

    def run_launcher(self, lines, env, args=()):
        text = "".join((m if isinstance(m, str) else json.dumps(m)) + "\n" for m in lines)
        proc = subprocess.run([sys.executable, "-I", str(LAUNCHER), *args], input=text.encode("utf-8"),
                              capture_output=True, env=env, timeout=60, cwd=str(self.project))
        out = proc.stdout.decode("utf-8", errors="replace").splitlines()
        return proc.returncode, out, proc.stderr.decode("utf-8", errors="replace")

    def fake_tool(self, name="tool"):
        folder = self.base / name
        folder.mkdir()
        (folder / "sf_papyrus_ref.py").write_text(FAKE_TOOL, encoding="utf-8")
        return folder


class StubTests(LauncherCase):
    def test_stub_answers(self):
        code, out, err = self.run_launcher([INIT, INITIALIZED, LIST, CALL, PING], self.env())
        self.assertEqual(code, 0, err)
        replies = [json.loads(line) for line in out]
        self.assertEqual([r["id"] for r in replies], [1, 2, 3, 4], "the notification must get no reply")
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", replies[0]["result"]["capabilities"])
        tools = replies[1]["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], ["papyrus_setup_help"])
        text = replies[2]["result"]["content"][0]["text"]
        self.assertFalse(replies[2]["result"]["isError"])
        self.assertIn("github.com/taosecurity/sf-papyrus-ref/releases", text)
        self.assertIn("SF_PAPYRUS_REF", text)
        self.assertEqual(replies[3]["result"], {})
        self.assertIn("help-only stub", err)

    def test_unknown_version_gets_newest(self):
        init = json.loads(json.dumps(INIT))
        init["params"]["protocolVersion"] = "1999-01-01"
        _, out, _ = self.run_launcher([init], self.env())
        self.assertEqual(json.loads(out[0])["result"]["protocolVersion"], "2025-11-25")

    def test_bad_lines_and_unknowns(self):
        lines = ["this is not json", "[1, 2]",
                 {"jsonrpc": "2.0", "id": 5, "method": "resources/list"},
                 {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "papyrus_lookup"}},
                 {"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": [1]},
                 PING]
        code, out, err = self.run_launcher(lines, self.env())
        self.assertEqual(code, 0, err)
        replies = [json.loads(line) for line in out]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["error"]["code"], -32600)
        self.assertEqual(replies[2]["error"]["code"], -32601)
        self.assertTrue(replies[3]["result"]["isError"])
        self.assertEqual(replies[4]["error"]["code"], -32602)
        self.assertEqual(replies[5]["id"], 4)

    def test_wrong_folder_is_reported(self):
        empty = self.base / "notthere"
        empty.mkdir()
        _, out, err = self.run_launcher([CALL], self.env(SF_PAPYRUS_REF=str(empty)))
        self.assertIn("holds no sf_papyrus_ref.py", json.loads(out[0])["result"]["content"][0]["text"])

    def test_placeholder_and_empty_values_ignored(self):
        env = self.env(CLAUDE_PLUGIN_OPTION_PAPYRUS_REF="")
        code, out, _ = self.run_launcher([], env, args=("--papyrus-ref", "${user_config.papyrus_ref}", "--find"))
        self.assertEqual(code, 1)
        self.assertEqual(out, ["not found"])


class PassThroughTests(LauncherCase):
    def check_echo(self, env, args=()):
        code, out, err = self.run_launcher([INIT, LIST], env, args)
        self.assertEqual(code, 0, err)
        self.assertEqual(out, ["echo:" + json.dumps(INIT), "echo:" + json.dumps(LIST)])
        self.assertIn("starting", err)

    def test_env_var(self):
        self.check_echo(self.env(SF_PAPYRUS_REF=str(self.fake_tool())))

    def test_plugin_option(self):
        self.check_echo(self.env(CLAUDE_PLUGIN_OPTION_PAPYRUS_REF=str(self.fake_tool())))

    def test_project_settings_file_ignored(self):
        # A cloned project must not choose the program the MCP server runs (security review, 0.1.0).
        folder = self.fake_tool()
        (self.project / ".claude").mkdir()
        (self.project / ".claude" / "starfield-modding.json").write_text(
            json.dumps({"papyrus_ref": str(folder)}), encoding="utf-8")
        code, out, _ = self.run_launcher([], self.env(), args=("--find",))
        self.assertEqual(code, 1)
        self.assertEqual(out, ["not found"])

    def test_user_settings_file_used_when_option_is_a_placeholder(self):
        folder = self.fake_tool()
        user = self.base / "user.json"
        user.write_text(json.dumps({"papyrus_ref": str(folder)}), encoding="utf-8")
        self.check_echo(self.env(SFMOD_USER_CONFIG=str(user),
                                 CLAUDE_PLUGIN_OPTION_PAPYRUS_REF="${user_config.papyrus_ref}"))

    def test_program_in_project_not_taken_from_path(self):
        (self.project / "sf_papyrus_ref.py").write_text(FAKE_TOOL, encoding="utf-8")
        env = self.env()
        env["PATH"] = str(self.project)
        env["PATHEXT"] = os.environ.get("PATHEXT", "") + ";.PY"
        code, out, _ = self.run_launcher([], env, args=("--find",))
        self.assertEqual(code, 1)
        self.assertEqual(out, ["not found"])

    def test_command_line_wins(self):
        good = self.fake_tool("good")
        bad = self.base / "bad"
        bad.mkdir()
        self.check_echo(self.env(SF_PAPYRUS_REF=str(bad)), args=("--papyrus-ref", str(good)))

    def test_path(self):
        folder = self.fake_tool()
        env = self.env()
        env["PATH"] = str(folder)
        env["PATHEXT"] = os.environ.get("PATHEXT", "") + ";.PY"
        self.check_echo(env)

    def test_exit_code_returned(self):
        folder = self.base / "failing"
        folder.mkdir()
        (folder / "sf_papyrus_ref.py").write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
        code, _, _ = self.run_launcher([], self.env(SF_PAPYRUS_REF=str(folder)))
        self.assertEqual(code, 3)


def real_tool_folder():
    for name in ("SFMOD_TEST_PAPYRUS_REF", "SF_PAPYRUS_REF"):
        folder = os.environ.get(name, "").strip()
        if folder and os.path.isfile(os.path.join(folder, "sf_papyrus_ref.py")):
            return folder
    return None


@unittest.skipUnless(real_tool_folder(), "no installed sf-papyrus-ref (set SFMOD_TEST_PAPYRUS_REF to its folder)")
class RealToolTest(LauncherCase):
    def test_real_server(self):
        lookup = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "papyrus_lookup", "arguments": {"name": "Debug.Trace"}}}
        code, out, err = self.run_launcher([INIT, INITIALIZED, LIST, lookup],
                                           self.env(SF_PAPYRUS_REF=real_tool_folder()))
        self.assertEqual(code, 0, err)
        replies = [json.loads(line) for line in out]
        self.assertEqual(replies[0]["result"]["serverInfo"]["name"], "sf-papyrus-ref")
        names = sorted(t["name"] for t in replies[1]["result"]["tools"])
        self.assertEqual(names, ["papyrus_check", "papyrus_list_flag", "papyrus_lookup", "papyrus_script"])
        self.assertFalse(replies[2]["result"]["isError"], replies[2])


class McpConfigTests(unittest.TestCase):
    def test_mcp_json_passes_the_papyrus_ref_option(self):
        # Claude Code does not export plugin options to MCP servers by itself (clean install test, NOTES.md),
        # so .mcp.json must hand the option to the launcher.
        with open(ROOT / ".mcp.json", encoding="utf-8") as f:
            server = json.load(f)["mcpServers"]["papyrus-ref"]
        self.assertEqual(server["env"], {"CLAUDE_PLUGIN_OPTION_PAPYRUS_REF": "${user_config.papyrus_ref}"})
        self.assertEqual(server["args"][-1], "${CLAUDE_PLUGIN_ROOT}/mcp/papyrus_ref_launcher.py")


if __name__ == "__main__":
    unittest.main()
