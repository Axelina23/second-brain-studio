# Changelog

Versions are dates: `2026.11.8.1444` means 8 November 2026, 14:44.
`app\build.ps1 -Stabile` uses the first section below as the release notes, so the newest version goes on top.
"Next version" collects what is in `main` but not released yet: rename it when it ships.

## Next version

- Renew expiring GitHub sign-ins automatically and preserve refresh credentials in the system vault across restarts and app updates. Keep public app updates available if GitHub sign-in expires.
- Recover from Codex background-server startup failures by retrying the same terminal once without the daemon, preserving the chat, prompt and permission settings.
- After an explicit in-chat manual save, use a bounded read-only verification instead of rewriting complete notes. Reuse confirmation only while chat and file hashes match; leave ordinary automatic saves unchanged.
- Simplify Codex model choices to the latest verified Luna, Terra, Sol and Astra versions; migrate older chat and notes defaults and remove the separate version selector.
- Customize terminal line spacing, colors, cursor shape and blinking, scrollback, smooth scrolling, right-click paste and panel position, with live updates.
- Keep Codex detectable after Windows installer restarts: avoid inheriting the installer's junction restrictions and fall back to the real standalone executable path.
- Add separate Claude, Codex and Antigravity settings for model, permission mode and reasoning effort. Keep notes models in Automatic notes.
- Adapt the window to the screen, retain proportional panel sizes, stack the terminal in narrow windows and allow resizing the notes list with mouse or keyboard.
- Fit terminal rows and columns during resizing and after fonts load; improve settings and chat layouts in small windows and with enlarged text.
- Add an opt-in setting for Codex full access without command approval prompts, applied to new chats, resumed chats and background notes.

## 2026.11.10.1247 - Reliable notes across assistants

- Detect assistants installed after the app starts: refresh the Windows executable search paths and installed-assistant list without requiring a restart.
- Retain a separate completion log for each saved chat, including simultaneous saves.
- Apply the current notes assistant to old chats too: save notes in the background without reopening the original assistant, and migrate the legacy Claude notes hook.
- Allow Codex to read local files during notes generation and require completion confirmation before marking notes saved.
- Fix undefined variables in the single unsaved-chat notice and the notes editor that could freeze the interface.

## 2026.11.10.0352 - Multi-assistant stable release

- Choose Claude, Codex or Antigravity for new chats, with assistant-specific model selectors and usage indicators.
- Resume, rename, pin, search, export, delete and restore chats across assistants. Show an assistant label for every chat.
- Each assistant can generate its own background notes and titles. Configure the assistant and model used for automatic notes.
- Keep chat titles stable while open and consistent across tabs, sidebar and lists; regenerate automatic titles from the context menu.
- Refresh saving status when background notes finish. Keep closed chats closed, report failed saves and offer retry.
- Sign in to Codex from Assistant accounts settings. Complete English translations for the startup-page selector and account controls.
- Hide background PowerShell hook windows. Hide Claude's native conversation fork action for other assistants.
- Notify when assistants finish or request input; preserve existing user hooks and status lines.
- Avoid discarding valid GitHub credentials after a transient authentication error. Refresh the Inbox count within ten seconds.

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
