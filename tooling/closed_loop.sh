#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
codex_dir="$(cd -- "${script_dir}/.." && pwd)"
repo_dir="$(cd -- "${codex_dir}/.." && pwd)"

spec_file="${codex_dir}/SPEC.md"
contract_file="${codex_dir}/CONTRACT.md"
acceptance_file="${codex_dir}/ACCEPTANCE.md"
matrix_file="${codex_dir}/TASK_MATRIX.yaml"

report_dir="${codex_dir}/build/closed-loop"
report_tsv="${report_dir}/report.tsv"
report_txt="${report_dir}/report.txt"
report_json="${report_dir}/report.json"

check_only=""

usage() {
  cat <<'USAGE'
Usage: tooling/closed_loop.sh [--check <name>]

Checks:
  preflight     Verify SPEC/CONTRACT/ACCEPTANCE/TASK_MATRIX exist
  build         Build codex-cheng binary
  hard-gate     Enforce rewrite hard gate from parity manifests + scenarios
  parity        Generate parity manifest and run codex-rs vs cheng parity scenarios
  tui           Run TUI interactive smoke check (offline)
  execpolicy    Run execpolicy smoke check (offline)
  completion    Run completion smoke check (offline)
  app-server    Run app-server generate-ts/json-schema smoke checks (offline)
  app           Run app command surface smoke check (offline)
  debug         Run debug command surface smoke check (offline)
  mcp           Run mcp add/list/get/remove smoke checks (offline)
  mcp-server    Run mcp-server initialize smoke check (offline)
  login-smoke   Run login smoke check (online)
  exec-smoke    Run exec smoke check (online)

Env:
  CODEX_CHENG_ONLINE=1          Enable online gates (login-smoke + exec-smoke)
  CODEX_CHENG_BIN=<path>        Override codex-cheng binary path
  CODEX_RS_DIR=<path>           Override codex-rs workspace path for parity checks
  CODEX_RS_BIN=<path>           Override codex-rs binary path for parity checks
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check)
      check_only="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" 1>&2
      usage
      exit 2
      ;;
  esac
done

mkdir -p "$report_dir"
: > "$report_tsv"

failures=0

join_cmd() {
  local out=""
  for part in "$@"; do
    out+="$part "
  done
  printf "%s" "${out% }"
}

record_step() {
  local name="$1"
  local status="$2"
  local code="$3"
  local cmd="$4"
  printf "%s\t%s\t%s\t%s\n" "$name" "$status" "$code" "$cmd" >> "$report_tsv"
}

run_step() {
  local name="$1"
  shift
  local cmd_str
  cmd_str=$(join_cmd "$@")
  echo "==> ${name}: ${cmd_str}"
  "$@"
  local code=$?
  if [ $code -eq 0 ]; then
    record_step "$name" "ok" "$code" "$cmd_str"
  else
    record_step "$name" "fail" "$code" "$cmd_str"
    failures=1
  fi
  return $code
}

skip_step() {
  local name="$1"
  local reason="$2"
  record_step "$name" "skip" 0 "$reason"
  echo "==> ${name}: skip (${reason})"
}

resolve_codex_bin() {
  local candidates=()
  if [ -n "${CODEX_CHENG_BIN:-}" ] && [ -x "${CODEX_CHENG_BIN}" ]; then
    candidates+=("${CODEX_CHENG_BIN}")
  fi
  if [ -x "${codex_dir}/build/cheng-codex" ]; then
    candidates+=("${codex_dir}/build/cheng-codex")
  fi
  if [ -x "${codex_dir}/build/codex-cheng" ]; then
    candidates+=("${codex_dir}/build/codex-cheng")
  fi
  if [ -x "${repo_dir}/codex-cheng-bin" ]; then
    candidates+=("${repo_dir}/codex-cheng-bin")
  fi
  if [ -x "${HOME}/cheng-lang/codex-cheng-bin" ]; then
    candidates+=("${HOME}/cheng-lang/codex-cheng-bin")
  fi
  if [ "${#candidates[@]}" -eq 0 ]; then
    return 1
  fi
  local cand=""
  for cand in "${candidates[@]-}"; do
    if "$cand" --version >/dev/null 2>&1; then
      printf "%s" "$cand"
      return 0
    fi
  done
  return 1
}

resolve_codex_rs_dir() {
  local candidates=()
  if [ -n "${CODEX_RS_DIR:-}" ]; then
    candidates+=("${CODEX_RS_DIR}")
  fi
  candidates+=("${codex_dir}/../../codex-lbcheng/codex-rs")
  candidates+=("${HOME}/codex-lbcheng/codex-rs")
  if [ "${#candidates[@]}" -eq 0 ]; then
    return 1
  fi
  local cand=""
  for cand in "${candidates[@]-}"; do
    if [ -f "${cand}/Cargo.toml" ] && [ -f "${cand}/cli/Cargo.toml" ]; then
      printf "%s" "$cand"
      return 0
    fi
  done
  return 1
}

check_preflight() {
  local missing=0
  for f in "$spec_file" "$contract_file" "$acceptance_file" "$matrix_file"; do
    if [ ! -s "$f" ]; then
      echo "missing or empty: $f" 1>&2
      missing=1
    fi
  done
  return $missing
}

check_build() {
  (cd "$codex_dir" && ./build.sh)
}

check_parity() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found" 1>&2
    return 2
  fi
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local rs_dir
  if ! rs_dir=$(resolve_codex_rs_dir); then
    echo "codex-rs workspace not found (set CODEX_RS_DIR)" 1>&2
    return 2
  fi
  (
    cd "$codex_dir" && \
    python3 tooling/parity/generate_manifest.py \
      --codex-rs-dir "$rs_dir" \
      --cheng-root "$codex_dir" \
      --out tooling/parity/parity_manifest.yaml
  )
  (
    cd "$codex_dir" && \
    python3 - <<'PY'
import json
from pathlib import Path
import sys

root = Path(".")
behavior = root / "tooling/parity/behavior_manifest.yaml"
if not behavior.exists():
    print("missing behavior manifest: tooling/parity/behavior_manifest.yaml", file=sys.stderr)
    raise SystemExit(2)
data = json.loads(behavior.read_text(encoding="utf-8"))
summary = data.get("summary", {})
total = int(summary.get("total_behaviors", 0))
implemented = int(summary.get("implemented", 0))
scenarized = int(summary.get("scenarized", 0))
if total <= 0 or implemented != total or scenarized != total:
    print(
        "behavior manifest summary invalid: "
        f"total={total} implemented={implemented} scenarized={scenarized}",
        file=sys.stderr,
    )
    raise SystemExit(2)
PY
  )
  (
    cd "$codex_dir" && \
    python3 tooling/parity/check_hard_gate.py \
      --cheng-root "$codex_dir"
  )
  (
    cd "$codex_dir" && \
    python3 tooling/parity/run_parity.py \
      --codex-rs-dir "$rs_dir" \
      --cheng-root "$codex_dir" \
      --cheng-bin "$bin"
  )
}

check_hard_gate() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found" 1>&2
    return 2
  fi
  (
    cd "$codex_dir" && \
    python3 tooling/parity/check_hard_gate.py \
      --cheng-root "$codex_dir"
  )
}

check_tui_surface() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  "$bin" --help > /dev/null
  grep -Fq "fn interactiveMenuChoiceTui" "${codex_dir}/src/interactive.cheng"
  grep -Fq "fn selectThreadIdTui" "${codex_dir}/src/exec_cmd.cheng"
  grep -Fq "isFeatureEnabled(\"tui2\")" "${codex_dir}/src/interactive.cheng"
  grep -Fq "isFeatureEnabled(\"tui2\")" "${codex_dir}/src/exec_cmd.cheng"
  grep -Fq "if len(args) == 0:" "${codex_dir}/src/main.cheng"
  grep -Fq "return runInteractiveWithOpts(rootOpts, \"\")" "${codex_dir}/src/main.cheng"
}

check_execpolicy() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local tmp_dir
  tmp_dir=$(mktemp -d)
  cat <<'RULE' > "${tmp_dir}/policy.rules"
prefix_rule(
    pattern = ["git", "push"],
    decision = "forbidden",
)
RULE
  "$bin" execpolicy check --rules "${tmp_dir}/policy.rules" git push origin main > "${tmp_dir}/out.json"
  grep -q '"decision"' "${tmp_dir}/out.json"
}

check_completion() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  "$bin" completion bash > /dev/null
}

check_app_server_generate() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local ts_dir="${tmp_dir}/ts"
  local json_dir="${tmp_dir}/json"
  "$bin" app-server generate-ts --out "$ts_dir" > /dev/null
  "$bin" app-server generate-json-schema --out "$json_dir" > /dev/null
  [ "$(find "$ts_dir" -type f -name '*.ts' | wc -l | tr -d ' ')" -gt 0 ]
  [ "$(find "$json_dir" -type f -name '*.json' | wc -l | tr -d ' ')" -gt 0 ]
}

check_app_surface() {
  if [ "$(uname -s 2>/dev/null || echo unknown)" != "Darwin" ]; then
    return 0
  fi
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  "$bin" app --help > /dev/null
}

check_debug_surface() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  "$bin" debug --help > /dev/null
}

check_mcp_surface() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local home_dir="${tmp_dir}/home"
  mkdir -p "${home_dir}"
  HOME="${home_dir}" "$bin" mcp add smoke -- /bin/echo hello > /dev/null
  HOME="${home_dir}" "$bin" mcp list > "${tmp_dir}/list.txt"
  grep -q "smoke" "${tmp_dir}/list.txt"
  HOME="${home_dir}" "$bin" mcp list --json > "${tmp_dir}/list.json"
  grep -q '"transport"' "${tmp_dir}/list.json"
  grep -q '"auth_status"' "${tmp_dir}/list.json"
  HOME="${home_dir}" "$bin" mcp get smoke > "${tmp_dir}/get.txt"
  grep -q "^smoke" "${tmp_dir}/get.txt"
  HOME="${home_dir}" "$bin" mcp get smoke --json > "${tmp_dir}/get.json"
  grep -q '"transport"' "${tmp_dir}/get.json"
  grep -q '"enabled_tools"' "${tmp_dir}/get.json"
  HOME="${home_dir}" "$bin" mcp remove smoke > /dev/null
  HOME="${home_dir}" "$bin" mcp list > "${tmp_dir}/list_after.txt"
  ! grep -q "smoke" "${tmp_dir}/list_after.txt"
}

check_mcp_server_surface() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local init_req='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}'
  local timeout_bin
  timeout_bin=$(command -v timeout || true)
  if [ -n "$timeout_bin" ]; then
    printf "%s\n" "$init_req" | "$timeout_bin" 3 "$bin" mcp-server > "${tmp_dir}/init.json"
  else
    printf "%s\n" "$init_req" | "$bin" mcp-server > "${tmp_dir}/init.json"
  fi
  grep -q '"id":1' "${tmp_dir}/init.json"
  grep -q '"result"' "${tmp_dir}/init.json"
  grep -q '"protocolVersion"' "${tmp_dir}/init.json"
}

check_login_smoke() {
  (cd "$codex_dir" && sh ./tooling/login_smoke.sh)
}

check_exec_smoke() {
  local bin
  if ! bin=$(resolve_codex_bin); then
    echo "codex-cheng binary not found" 1>&2
    return 2
  fi
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local last_msg="${tmp_dir}/last_message.txt"
  "$bin" exec --json --output-last-message "$last_msg" "Say OK." > /dev/null
  [ -s "$last_msg" ]
}

run_selected() {
  case "$1" in
    preflight) run_step "preflight" check_preflight ;;
    build) run_step "build" check_build ;;
    hard-gate) run_step "hard-gate" check_hard_gate ;;
    parity) run_step "parity" check_parity ;;
    tui) run_step "tui" check_tui_surface ;;
    execpolicy) run_step "execpolicy" check_execpolicy ;;
    completion) run_step "completion" check_completion ;;
    app-server) run_step "app-server" check_app_server_generate ;;
    app) run_step "app" check_app_surface ;;
    debug) run_step "debug" check_debug_surface ;;
    mcp) run_step "mcp" check_mcp_surface ;;
    mcp-server) run_step "mcp-server" check_mcp_server_surface ;;
    login-smoke) run_step "login-smoke" check_login_smoke ;;
    exec-smoke) run_step "exec-smoke" check_exec_smoke ;;
    *)
      echo "Unknown check: $1" 1>&2
      usage
      exit 2
      ;;
  esac
}

if [ -n "$check_only" ]; then
  run_selected "$check_only"
else
  run_selected preflight
  run_selected build
  run_selected hard-gate
  run_selected parity
  run_selected tui
  run_selected execpolicy
  run_selected completion
  run_selected app-server
  run_selected app
  run_selected debug
  run_selected mcp
  run_selected mcp-server
  if [ "${CODEX_CHENG_ONLINE:-}" = "1" ]; then
    run_selected login-smoke
    run_selected exec-smoke
  else
    skip_step "login-smoke" "CODEX_CHENG_ONLINE not set"
    skip_step "exec-smoke" "CODEX_CHENG_ONLINE not set"
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  REPORT_TSV="$report_tsv" REPORT_JSON="$report_json" python3 - <<'PY'
import json
import os
import time

tsv = os.environ["REPORT_TSV"]
report = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
with open(tsv, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t", 3)
        name, status, code, cmd = (parts + ["", "", "", ""])[:4]
        report["steps"].append({
            "name": name,
            "status": status,
            "exit_code": int(code) if code.isdigit() else 0,
            "command": cmd,
        })

report["result"] = "fail" if any(s["status"] == "fail" for s in report["steps"]) else "pass"

with open(os.environ["REPORT_JSON"], "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY
else
  echo "python3 not found; skipping JSON report" 1>&2
fi

{
  echo "Closed loop report"
  echo "- result: $(if [ $failures -eq 0 ]; then echo pass; else echo fail; fi)"
  echo "- report.tsv: ${report_tsv}"
  echo "- report.json: ${report_json}"
} > "$report_txt"

if [ $failures -ne 0 ]; then
  exit 1
fi
