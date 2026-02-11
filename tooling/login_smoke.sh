#!/bin/sh
set -eu

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
codex_dir="$(cd -- "${script_dir}/.." && pwd)"
repo_dir="$(cd -- "${codex_dir}/.." && pwd)"

env_file="${codex_dir}/.env"
if [ -f "$env_file" ]; then
  # shellcheck source=/dev/null
  set -a
  . "$env_file"
  set +a
fi

codex_bin="${CODEX_CHENG_BIN:-}"
if [ -z "$codex_bin" ] && [ -x "${codex_dir}/build/codex-cheng" ]; then
  codex_bin="${codex_dir}/build/codex-cheng"
fi
if [ -z "$codex_bin" ] && [ -x "${repo_dir}/codex-cheng-bin" ]; then
  codex_bin="${repo_dir}/codex-cheng-bin"
fi
if [ -z "$codex_bin" ] || [ ! -x "$codex_bin" ]; then
  echo "Missing codex binary. Build it first with:"
  echo "  ./build.sh"
  exit 3
fi

tmp_dir="${repo_dir}/.tmp_codex_login"
mkdir -p "$tmp_dir"
last_msg="${tmp_dir}/last_message.txt"

api_key="${OPENAI_API_KEY:-${CODEX_API_KEY:-}}"
if [ -n "$api_key" ]; then
  printf "%s" "$api_key" | "$codex_bin" login --with-api-key >/dev/null 2>&1
else
  wait_secs="${CODEX_LOGIN_WAIT_SECS:-300}"
  poll_interval=2
  echo "No API key found. Starting browser OAuth login..."
  "$codex_bin" login >/dev/null 2>&1 &
  login_pid=$!
  elapsed=0
  while [ "$elapsed" -lt "$wait_secs" ]; do
    if [ -f "${HOME}/.codex-cheng/auth.json" ] || [ -f "${HOME}/.codex/auth.json" ]; then
      break
    fi
    sleep "$poll_interval"
    elapsed=$((elapsed + poll_interval))
  done
  if [ ! -f "${HOME}/.codex-cheng/auth.json" ] && [ ! -f "${HOME}/.codex/auth.json" ]; then
    echo "OAuth login not completed within ${wait_secs}s."
    kill "$login_pid" >/dev/null 2>&1 || true
    exit 4
  fi
  wait "$login_pid" >/dev/null 2>&1 || true
fi

if [ ! -f "${HOME}/.codex-cheng/auth.json" ] && [ ! -f "${HOME}/.codex/auth.json" ]; then
  echo "Login did not create auth.json. Check network or API key validity."
  exit 4
fi

"$codex_bin" exec --json --output-last-message "$last_msg" "Say OK." >/dev/null 2>&1

if [ ! -s "$last_msg" ]; then
  echo "Exec failed: no output written to ${last_msg}."
  exit 5
fi

echo "codex-cheng login + exec smoke test: OK"
