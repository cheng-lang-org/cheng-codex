# Codex Cheng Port

This directory hosts the Cheng rewrite of Codex. The goal is to reimplement
Codex CLI/TUI behavior in Cheng while keeping parity with the existing Rust
implementation in this repo.

## Scope

- Cheng implementation of `codex-rs` CLI command surface.
- Production closed-loop delivery with offline + optional online gates.
- 100% native Cheng implementation; no delegation to `codex-rs`.

## Build

This project currently expects the Cheng toolchain from the cheng-lang repo
(renamed from cheng-lang).
Set `CHENG_ROOT` to your cheng-lang checkout (default: `../cheng-lang`) and run:

```
cd "$CHENG_ROOT"
./src/tooling/chengc.sh /absolute/path/to/cheng-codex/src/main.cheng --name:cheng-codex
```

The `chengc.sh` script outputs the binary into the cheng-lang root with the
name provided via `--name`.

You can also use the helper script:

```
./cheng-codex/build.sh
```

## Status

- Full CLI command surface wired in `src/main.cheng`.
- App-server, cloud, execpolicy, responses proxy, stdio relay and feature controls available.
- MCP / MCP Server / debug paths are all implemented natively in Cheng.
- Plan mode parity is landed: `<proposed_plan>` parsing, `item/plan/delta`, and `request_user_input` protocol surface are implemented.
- `arg0` parity is tightened to codex-rs semantics: argv0 dispatch (`apply_patch` / `applypatch` / `codex-linux-sandbox`), dotenv filtering (`CODEX_*` blocked), and PATH helper aliases under `CODEX_HOME/tmp/arg0`.
- `apply_patch` supports all three parity paths: argv0 aliases, hidden `--codex-run-as-apply-patch`, and hidden root command tokens (`apply_patch` / `applypatch`).
- Legacy `notify` hook parity is implemented (`notify=[...]` appends `agent-turn-complete` JSON payload).
- Tool lifecycle hook channel is wired with `after_tool_use` internal payload shape and turn/call context propagation.
- Parity manifest currently reports `61/61` workspace crates mapped as implemented.
- Behavior manifest is added at `tooling/parity/behavior_manifest.yaml` to track behavior-level (not only crate-level) coverage.
- Final dual-view coverage snapshot is available at `tooling/parity/coverage_table.md`.
- Dual-run parity framework in `tooling/parity/` (manifest + scenario diff reports).
- Closed-loop gate runner: `tooling/closed_loop.sh` (preflight/build/parity/execpolicy/completion/app-server/debug/mcp + optional online smoke).
