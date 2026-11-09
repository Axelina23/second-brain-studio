# Changelog

Versions are dates: `2026.11.8.1444` means 8 November 2026, 14:44.
`app\build.ps1 -Stabile` uses the first section below as the release notes, so the newest version goes on top.
"Next version" collects what is in `main` but not released yet: rename it when it ships.

## Next version (not released yet)

- **Fix: GitHub no longer asks you to reconnect every day.** A single "401" answer from GitHub made the app throw away
  a perfectly valid key. Now the app checks the key again on `/user` first and removes it only if GitHub refuses it
  twice; every 401 is written to `app-errori.log` with the call, the URL and GitHub's answer (never the key).
- The Inbox counter follows the folder within 10 seconds, also when the Inbox is emptied from a terminal.

- Plan usage bars also for people who already had their own Claude Code status line: the app keeps it and runs it
  after saving the usage numbers, so the line looks exactly as before.

## 2026.11.8.1805 — First public release

The first version for everyone. Everything below is new.

**Home and pages**
- **Today**: alerts (chats closed without saving notes, stale projects, Inbox), project tiles colored by how fresh their notes are, chats to resume, next deadlines.
- **Chats**: every chat grouped by day, with keywords and save status; save, rename, delete and restore from the bin.
- **Notes**: Markdown reader with a freshness dot for every file, full-text search and quick edits.
- **Map**: eight views of your second brain (2D and 3D graph, mosaic, sunburst, activity calendar, metro, city, orbits), colored by area or by freshness.
- **Inbox**: drop files on the window and they land in the Inbox folder, ready to be sorted by Claude.

**Claude Code inside**
- The real `claude.exe` in tabs (ConPTY + xterm.js): your plan, your hooks, your MCP servers.
- Closing a tab lets Claude exit cleanly, so the end-of-session hook runs and the notes are saved.
- Windows notifications when Claude has finished or is waiting for a permission; click one and the right tab opens.
- Claude can open a new chat in a new tab of the app.
- Plan usage (5-hour window and week) in the status bar.

**Sync and multiple PCs**
- GitHub sign-in with a device code (the app never sees your password), private repo creation, one-click sync, conflicts handed to Claude.
- Chats from your other PCs, live and read-only, through a small summary on a branch of your own repo (never the messages).

**Setup and settings**
- Guided first run: create a new second brain, adopt an existing folder or download yours from GitHub; a short questionnaire writes your rules and index.
- English or Italian from the first screen (it starts in the language of Windows): the second brain is created in that language, folders included (`INDEX.md`, `Me/`, `Projects/`, `Archive/Log.md`…). The areas you pick become folders and show up in Notes and on the Map.
- Settings in ten sections: theme (dark, light, follow Windows), accent color, text size, notifications with quiet hours, terminal, automatic notes, sync, shortcuts, data.
- Italian and English interface.
- Automatic updates from GitHub Releases, checked with SHA-256; test builds only if you turn them on.
