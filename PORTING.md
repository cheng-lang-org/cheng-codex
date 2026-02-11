# Codex Cheng Porting Checklist (WIP)

This file tracks parity between codex-rs (Rust) and codex-cheng (Cheng).
Status tags: TODO, WIP, DONE.

## CLI surface (codex-rs/cli)
- TODO: Subcommands (exec, review, login/logout, mcp, mcp-server, app-server, completion, sandbox, execpolicy, apply, resume, fork, cloud, responses-api-proxy, stdio-to-uds, features).
- TODO: Global flags and config overrides (profile, sandbox, approvals, model, oss/local provider, images, cwd, full-auto, yolo).
- TODO: Completion generation parity (bash/zsh/fish/etc).
- TODO: Exit messaging + update action.

## Exec (codex-rs/exec)
- TODO: Exec CLI options and JSONL output mode.
- TODO: Review command wiring via exec.
- TODO: Resume command wiring via exec.
- TODO: Event processor parity (human/jsonl).

## Core (codex-rs/core)
- TODO: Config loader (config.toml, profiles, overrides, schema).
- TODO: Features flags system and stage info.
- TODO: Model providers and model selection.
- TODO: Auth store + login flows.
- TODO: Agent loop, tools, approvals, sandbox policy.
- TODO: Context manager + compacting.
- TODO: Git info and project trust.
- TODO: Notifications and OTEL.
- WIP: model client supports responses/chat wire API selection.

## Protocol (codex-rs/protocol)
- TODO: Shared types (threads, turns, items, approvals, config types).
- TODO: Plan tool schema and event mapping.

## App server (codex-rs/app-server + app-server-protocol)
- TODO: JSON-RPC protocol parity.
- TODO: Thread/turn/items lifecycle and notifications.
- TODO: Generate TS/JSON schema tooling.
- WIP: configRequirements/read wired to requirements.toml + managed_config.toml.
- WIP: fuzzyFileSearch implemented (simple subsequence match + per-root limit).

## MCP (codex-rs/mcp-server + mcp-types + rmcp-client)
- TODO: MCP client config + OAuth flows.
- TODO: MCP server implementation (stdio transport).

## TUI (codex-rs/tui + tui2)
- TODO: Legacy TUI parity.
- WIP: TUI2 interactive UX (ANSI full-screen chat view + session picker) in pure Cheng.
- TODO: Ratatui-like layout and snapshot-driven output (multi-pane, scrolling, overlays, key-event loop).

## Storage/history
- TODO: History.jsonl parity and thread storage.

## Sandbox + execpolicy
- TODO: Sandbox runners (seatbelt/landlock/windows).
- TODO: Execpolicy check subcommand.
