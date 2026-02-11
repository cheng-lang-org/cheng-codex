# Codex Cheng Port

This directory hosts the Cheng rewrite of Codex. The goal is to reimplement
Codex CLI/TUI behavior in Cheng while keeping parity with the existing Rust
implementation in this repo.

## Scope

- Cheng implementation of `codex-rs` CLI command surface.
- Production closed-loop delivery with offline + optional online gates.
- 100% 原生 Cheng 实现，不依赖 codex-rs 委托。

## Build

This project currently expects the Cheng toolchain from the cheng-lang repo
(renamed from cheng-lang).
Set `CHENG_ROOT` to your cheng-lang checkout (default: `../cheng-lang`) and run:

```
cd "$CHENG_ROOT"
./src/tooling/chengc.sh /absolute/path/to/codex-cheng/src/main.cheng --name:codex-cheng
```

The `chengc.sh` script outputs the binary into the cheng-lang root with the
name provided via `--name`.

You can also use the helper script:

```
./codex-cheng/build.sh
```

## Status

- Full CLI command surface wired in `src/main.cheng`.
- App-server, cloud, execpolicy, responses proxy, stdio relay and feature controls available.
- MCP / MCP Server / debug 路径均为原生 Cheng 实现。
- Closed-loop gate runner: `tooling/closed_loop.sh` (preflight/build/execpolicy/completion/app-server/debug/mcp + optional online smoke).
