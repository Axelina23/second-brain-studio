# Security policy

## Supported versions

Only the latest release receives fixes. Update with the in-app "Update ready" button
or download the newest version from [Releases](../../releases/latest).

## Reporting a vulnerability

Please do **not** open a public issue for a security problem.
Use GitHub's private reporting instead: [Report a vulnerability](../../security/advisories/new).

Include the app version, what you did and what happened. This is a spare-time project:
expect a first answer within a few days, not hours.

## Good to know

- Second Brain Studio runs the CLIs you already have (Claude Code, Codex, Antigravity) with their own accounts.
  It never stores their passwords or keys.
- The GitHub token used for sync is kept in the Windows credential store, not in the notes folder.
- The app is not code-signed yet, so Windows SmartScreen shows a warning on first run.
  The SHA256 of each release file is shown next to it on the Releases page, so you can compare it.
