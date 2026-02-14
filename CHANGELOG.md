# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-11

Initial public release.

### Added

- **Epic lifecycle** — `ft epic create`, `list`, `health`, `close` with YAML spec parsing and dependency validation
- **Task management** — 9-state lifecycle (pending → in_progress → completed/cancelled + IPC states), dependencies, guards, acceptance criteria
- **Worker orchestration** — `ft work spawn` with tmux sessions, crash detection, automatic chain spawning of dependent tasks
- **Completion rules engine** — 22 built-in rules (round cap, blocking findings, required reviews, TDD gate, doc-guard) with env var overrides
- **Review system** — `ft review` with self-critique gating, disposition workflow, finding-to-task pipeline
- **TUI dashboard** — `ft work dashboard` with real-time worker status, keyboard navigation
- **Git worktree integration** — automatic branch creation, worktree reuse, PR detection
- **Hook validators** — PreToolUse hooks for TDD enforcement, documentation guard, security checks, stub detection
- **Schema migrations** — automatic database setup via `ft setup` with versioned migrations
- **CLI** — `ft <noun> <verb>` pattern with `--json` output, `--dry-run`, preflight checks
- **Install scripts** — `install.sh` (local) and `web-install.sh` (curl-pipe) bootstrapping

[0.1.0]: https://github.com/davidabeyer/formaltask/releases/tag/v0.1.0
