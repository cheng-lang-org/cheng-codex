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
- Closed-loop gate runner: `tooling/closed_loop.sh` (preflight/build/execpolicy/completion/app-server/debug/mcp + optional online smoke).
