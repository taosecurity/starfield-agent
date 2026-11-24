# Privacy

starfield-agent is a plugin for Claude Code. The plugin itself runs on your own computer. It collects no data and makes
no network connections of its own.

## What the plugin does not do

- It has no telemetry, analytics, crash reporting or update checks.
- It never uploads anything. Uploads to Nexus Mods and Bethesda Creations are for you to do.
- It never changes the game's files, your saves or your load order. Its guards refuse such changes.

## What goes to Claude

The plugin is instructions and guards for Claude Code, so the AI assistant is part of the picture. Claude Code sends
your conversation, and every file and command output the assistant reads while it works for you, to Anthropic's
servers. What Anthropic does with that is covered by Claude Code's own terms and privacy policy, not by this plugin.
The skills tell the assistant to run the public modding tools and read their output, so a skill such as `log-review`
or `evaluate-mod` puts the logs and plugin names it reads into the conversation. Check what you are asking it to
read before you ask, and keep your own private notes and saves out of the project folder if you don't want them read.

## What it reads

- the settings files, in this order: the environment variables `SFMOD_GAME_DIR`, `SFMOD_SAVES_DIR`,
  `SFMOD_EXTRA_GUARDED` and `SF_PAPYRUS_REF`; the plugin options; the project's `.claude\starfield-agent.json`; and
  your `%APPDATA%\starfield-agent\starfield-agent.json` (on Linux and macOS
  `~/.config/starfield-agent/starfield-agent.json`);
- for each command or file edit the assistant is about to make, the hooks read the command text and the file paths,
  to see whether it touches a guarded folder (the game's `Data` folder, the saves folder, `Plugins.txt`,
  `ContentCatalog.txt` and any folder you add);
- before a `git add`, `git commit`, `git push`, `gh release` or `gh gist create`, the game-code guard lists the files
  that command would carry and reads the first 4,096 bytes of each, to see whether it holds Bethesda's files or
  script code.

## What it writes

The hooks write nothing, with one exception you turn on yourself: if you set the environment variable `SFMOD_HOOK_LOG`
to a file path, both guards append what they read and decided to that file. The Papyrus lookup server writes a log
only when started with `--log <file>`. The `setup` skill writes the settings file named above, and only after you
agree.

The skills run the public tools (sf-mod-build, sf-mod-check, sf-papyrus-ref, sf-test-plan, sf-load-order and others).
What those tools write is covered by their own PRIVACY.md files.

## Other programs it starts

The game-code guard runs `git` on the repository of the command it checks, and, when it is installed, `sf-papyrus-ref`
to ask whether a script name is one of the official scripts. The Papyrus lookup server (`papyrus-ref`) starts
`sf-papyrus-ref` from the folder you set in the `papyrus_ref` option. Both run on your computer, and neither
connects to the network.

## Personal data

The plugin handles none of its own. Logs you ask for can hold folder paths with your Windows user name; read them
before you share them.

## Downloading it

Installing the plugin from GitHub is covered by GitHub's own
[privacy statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement).
starfield-agent's author receives only the public download counts GitHub shows.

## Questions

Open an issue at https://github.com/taosecurity/starfield-agent/issues.
