# Changelog

Versions are dates: `2026.11.8.1444` means 8 November 2026, 14:44.
`app\build.ps1 -Stabile` uses the first section below as the release notes, so the newest version goes on top.
"Next version" collects what is in `main` but not released yet: rename it when it ships.

## Next version (not released yet)

- **New chat with tabs already open asks which assistant and model to use**, instead of reopening the last one.
  Model choice now also for Codex (Luna, Terra, Sol and Astra, with a version toggle between 5.6 and 6/6.1) and
  Antigravity (Settings → Terminal).
- **Each assistant does its own background work.** Notes at the end of a Codex or Antigravity chat, chat keywords
  and quick-note titles are written by the chat's own assistant, so Claude's plan is not used. Settings → Automatic
  notes lets you pick who writes the notes ("Chat's own", Claude, Codex, Antigravity) and the model for each.
- **Delete and restore also for Codex and Antigravity chats** (bin kept 30 days, Settings → Data).
- **Windows notification when Antigravity asks you a question.**
- **Status bar usage follows the assistant in use**: Claude plan bars, Codex limits when available, otherwise
  messages in the last 5 hours and 7 days.

- **Choose the assistant and the model for a new chat.** When no chat is open, the terminal panel lets you pick
  Claude, Codex or Antigravity (`agy`), and for Claude the model (Default, Fable, Opus, Sonnet, Haiku). The same
  choice is in Settings → Terminal and is used by every "New chat" button, Briefing and Review included. Codex and
  Antigravity must already be installed and signed in; they run with their own model and subscription.
- **Codex and Antigravity chats work like Claude's.** Chats started in your second brain folder are listed in Chats
  and Today with the assistant's name, and you can resume, rename, pin, search and export them. When you close
  their tab the notes are updated automatically (same background step as for Claude) and the second brain is
  synced. On first use the app adds its hooks to Codex (`~/.codex/hooks.json`) and Antigravity
  (`~/.gemini/config/hooks.json`) for the "has finished" notification and the sync at chat start, and creates an
  `AGENTS.md` in the second brain that points them to your rules and index. Codex asks you to approve hooks once:
  type `/hooks` in a Codex chat. Not available for these chats: delete, duplicate, open in another folder, and the
  "waiting for permission" notification for Antigravity. Chats started outside the app are listed, but their notes
  are saved only with "Save notes".
- **Fix: the "Claude has finished" notification never arrived.** The hook wrote an empty event (a PowerShell
  variable name clash), so the app ignored it.

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
