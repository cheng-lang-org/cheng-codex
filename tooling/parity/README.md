# parity tooling

This directory contains semantic parity checks between:

- baseline: `codex-rs` (pinned baseline commit)
- target: `cheng-codex`

## Files

- `module_map.yaml`: crate -> Cheng module mapping input.
- `generate_manifest.py`: generates `parity_manifest.yaml` from the mapping + source trees.
- `behavior_manifest.yaml`: behavior-level parity coverage (arg0/hooks/plan-mode/...).
- `coverage_table.md`: crate + behavior dual-view final coverage snapshot.
- `run_parity.py`: executes scenario suites against both binaries and produces reports.
- `scenarios/*.yaml`: parity scenarios (JSON-encoded YAML).

## Run

From `cheng-codex` root:

```bash
python3 tooling/parity/generate_manifest.py \
  --codex-rs-dir /path/to/codex-rs \
  --cheng-root .

python3 tooling/parity/run_parity.py \
  --codex-rs-dir /path/to/codex-rs \
  --cheng-root . \
  --cheng-bin ./build/codex-cheng
```

Outputs:

- `tooling/parity/parity_manifest.yaml`
- `tooling/parity/behavior_manifest.yaml`
- `build/parity/report.json`
- `build/parity/report.txt`

Current baseline snapshot (codex-rs `main@ebe359b8`): manifest summary is `61/61 implemented`.
Behavior snapshot: `behavior_manifest.yaml` is `implemented=20`, `scenarized=20`, `verification_status=pending_execution`.

## Environment overrides

- `CODEX_RS_DIR`: fallback codex-rs workspace path.
- `CODEX_RS_BIN`: use prebuilt baseline binary instead of `cargo run`.
- `CODEX_CHENG_BIN`: override Cheng binary path.
