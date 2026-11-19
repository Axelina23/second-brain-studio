# Code signing policy

Windows installers of Second Brain Studio are meant to be code-signed so that Windows can show who published them.

**Status:** an application to the free signing program of the SignPath Foundation has been submitted or is being prepared.
Until a certificate is issued, installers are **not signed** and Windows SmartScreen shows a warning on first run
(*More info > Run anyway*). This page will be updated when signing is active.

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## What gets signed

Only the Windows installer (`Second Brain Studio Setup <version>.exe`) and the program inside it, built from the source code in this
repository by the [Release workflow](.github/workflows/release.yml) on GitHub Actions, from a tagged commit.
Nothing is signed from a developer's computer, and no third-party binaries are signed.

## Team and roles

Second Brain Studio is a one-person project.

| Role | Person |
|---|---|
| Author (committer) | [Francesco Cinquegrana](https://github.com/Axelina23) |
| Reviewer (reviews changes from non-committers) | [Francesco Cinquegrana](https://github.com/Axelina23) |
| Approver (approves each signing request) | [Francesco Cinquegrana](https://github.com/Axelina23) |

Every signing request is approved manually. The team member uses multi-factor authentication for GitHub and for SignPath.

## Privacy statement

Second Brain Studio has no telemetry, no analytics and no accounts of its own. It transfers information to other networked systems only as follows:

- **GitHub (`github.com`, `api.github.com`):** to check for new versions (this can be turned off in *Settings > General > Updates*),
  and, only if you sign in to GitHub in the app, to sync *your own* private notes repository and your chats' status between your PCs.
- **Claude Code, Codex and Antigravity** are separate programs that you install and sign in to yourself. Second Brain Studio only starts them on your computer;
  what they send to their providers is governed by their own privacy policies.
- **Local AI** (optional) talks only to a llama.cpp server on your own computer (`127.0.0.1`).
- The Ko-fi link opens in your browser only when you click it.

Your notes stay in a folder on your computer. See the [security policy](SECURITY.md) for how to report a problem.
