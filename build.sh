#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/src/main.cheng"
OUT_DIR="$ROOT/build"
if [ ! -f "$SRC" ]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  SRC="$ROOT/cheng-codex/src/main.cheng"
  OUT_DIR="$ROOT/cheng-codex/build"
fi
if [ -z "${CHENG_ROOT:-}" ]; then
  if [ -d "$ROOT/../cheng-lang" ]; then
    CHENG_ROOT="$ROOT/../cheng-lang"
  elif [ -d "$ROOT/../../cheng-lang" ]; then
    CHENG_ROOT="$ROOT/../../cheng-lang"
  elif [ -d "${HOME}/cheng-lang" ]; then
    CHENG_ROOT="${HOME}/cheng-lang"
  else
    CHENG_ROOT="$ROOT/../cheng-lang"
  fi
fi
CHENG_ROOT="$(cd "$CHENG_ROOT" && pwd)"
NAME="cheng-codex-bin"
OUT_NAME="cheng-codex"
WORKSPACE_ROOT="$CHENG_ROOT/chengcache/workspace"
mkdir -p "$WORKSPACE_ROOT"

if [ "${CODEX_BUILD_VERBOSE:-1}" != "0" ]; then
  echo "[cheng-codex] build: stage1 -> backend driver (obj/exe) -> link (this can take a few minutes)"
fi
export CHENG_BACKEND_LINKER="${CHENG_BACKEND_LINKER:-self}"
export CHENG_BACKEND_FRONTEND="${CHENG_BACKEND_FRONTEND:-mvp}"
if [ "${CODEX_BUILD_FAST:-0}" = "1" ]; then
  export CFLAGS="${CFLAGS:--O0}"
fi
TRACE_INTERVAL="${CODEX_BUILD_TRACE_INTERVAL:-5}"
TRACE_HEARTBEAT="${CODEX_BUILD_TRACE_HEARTBEAT:-60}"

file_size_bytes() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "0"
    return
  fi
  local size=""
  size="$(stat -f%z "$path" 2>/dev/null || true)"
  if [ -n "$size" ]; then
    echo "$size"
    return
  fi
  size="$(stat -c%s "$path" 2>/dev/null || true)"
  if [ -n "$size" ]; then
    echo "$size"
    return
  fi
  local wc_out=""
  wc_out="$(wc -c "$path" 2>/dev/null || true)"
  if [ -n "$wc_out" ]; then
    echo "$wc_out" | awk '{print $1}'
    return
  fi
  echo "0"
}

append_pkg_root() {
  local root="$1"
  if [ -z "$root" ] || [ ! -d "$root" ]; then
    return
  fi
  case ",${CHENG_PKG_ROOTS:-}," in
    *,"$root",*) return ;;
  esac
  if [ -z "${CHENG_PKG_ROOTS:-}" ]; then
    CHENG_PKG_ROOTS="$root"
  else
    CHENG_PKG_ROOTS="$CHENG_PKG_ROOTS,$root"
  fi
}

probe_backend_driver() {
  local driver="$1"
  if [ -z "$driver" ] || [ ! -x "$driver" ]; then
    return 1
  fi
  local probe_target="${CHENG_BACKEND_TARGET:-}"
  if [ -z "$probe_target" ] && [ -x "$CHENG_ROOT/src/tooling/detect_host_target.sh" ]; then
    probe_target="$(sh "$CHENG_ROOT/src/tooling/detect_host_target.sh" 2>/dev/null || true)"
  fi
  if [ -z "$probe_target" ]; then
    probe_target="arm64-apple-darwin"
  fi
  local probe_obj="$CHENG_ROOT/chengcache/.codex_driver_probe.$$.$RANDOM.o"
  rm -f "$probe_obj"
  env \
    CHENG_BACKEND_ALLOW_NO_MAIN=1 \
    CHENG_BACKEND_WHOLE_PROGRAM=1 \
    CHENG_BACKEND_TARGET="$probe_target" \
    CHENG_BACKEND_EMIT=obj \
    CHENG_BACKEND_FRONTEND=mvp \
    CHENG_BACKEND_INPUT="$CHENG_ROOT/src/std/system_helpers_backend.cheng" \
    CHENG_BACKEND_OUTPUT="$probe_obj" \
    "$driver" >/dev/null 2>&1
  local code=$?
  if [ $code -ne 0 ] || [ ! -s "$probe_obj" ]; then
    rm -f "$probe_obj"
    return 1
  fi
  rm -f "$probe_obj"
  return 0
}

if [ -d "$ROOT/../cheng-libp2p" ]; then
  LIBP2P_SRC="$(cd "$ROOT/../cheng-libp2p" && pwd)"
  LIBP2P_WORK="$WORKSPACE_ROOT/cheng-libp2p"
  mkdir -p "$LIBP2P_WORK"
  if [ -d "$LIBP2P_SRC/cheng" ]; then
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "$LIBP2P_SRC/cheng/" "$LIBP2P_WORK/cheng/"
    else
      rm -rf "$LIBP2P_WORK/cheng"
      mkdir -p "$LIBP2P_WORK/cheng"
      cp -R "$LIBP2P_SRC/cheng/" "$LIBP2P_WORK/cheng/"
    fi
  elif [ -d "$LIBP2P_SRC/src" ]; then
    mkdir -p "$LIBP2P_WORK/cheng/libp2p"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "$LIBP2P_SRC/src/" "$LIBP2P_WORK/cheng/libp2p/"
    else
      rm -rf "$LIBP2P_WORK/cheng/libp2p"
      mkdir -p "$LIBP2P_WORK/cheng/libp2p"
      cp -R "$LIBP2P_SRC/src/" "$LIBP2P_WORK/cheng/libp2p/"
    fi
  fi
  if [ -f "$LIBP2P_SRC/cheng-package.toml" ]; then
    cp "$LIBP2P_SRC/cheng-package.toml" "$LIBP2P_WORK/cheng-package.toml"
  fi
  append_pkg_root "$LIBP2P_WORK"
fi
export CHENG_PKG_ROOTS="${CHENG_PKG_ROOTS:-}"

CHENGC_SCRIPT=""
if [ -x "$CHENG_ROOT/cheng/tooling/chengc.sh" ]; then
  CHENGC_SCRIPT="$CHENG_ROOT/cheng/tooling/chengc.sh"
elif [ -x "$CHENG_ROOT/src/tooling/chengc.sh" ]; then
  CHENGC_SCRIPT="$CHENG_ROOT/src/tooling/chengc.sh"
fi

if [ -z "$CHENGC_SCRIPT" ]; then
  echo "[cheng-codex] missing cheng toolchain at: $CHENG_ROOT" 1>&2
  echo "[cheng-codex] expected chengc at: cheng/tooling/chengc.sh or src/tooling/chengc.sh" 1>&2
  exit 1
fi

# Prefer a verified backend driver. This avoids silently falling back to
# stage0 lexer binaries that cannot compile the workspace.
if [ -z "${CHENG_BACKEND_DRIVER:-}" ]; then
  driver_candidates=(
    "$CHENG_ROOT/driver_regr2"
    "$CHENG_ROOT/driver_local_patch2"
    "$CHENG_ROOT/driver_local_patch"
    "$CHENG_ROOT/driver_local"
    "$CHENG_ROOT/build/driver_probe3"
    "$CHENG_ROOT/cheng"
    "$CHENG_ROOT/artifacts/backend_selfhost_self_obj/cheng.stage2"
    "$CHENG_ROOT/bin/cheng-stage0"
  )
  for cand in "${driver_candidates[@]}"; do
    if probe_backend_driver "$cand"; then
      export CHENG_BACKEND_DRIVER="$cand"
      break
    fi
  done
fi
if [ -z "${CHENG_BACKEND_DRIVER:-}" ]; then
  echo "[cheng-codex] no usable backend driver found under $CHENG_ROOT" 1>&2
  echo "[cheng-codex] hint: rebuild driver and ensure it can compile src/std/system_helpers_backend.cheng" 1>&2
  exit 1
fi
if [ ! -f "$SRC" ]; then
  echo "[cheng-codex] source not found: $SRC" 1>&2
  exit 1
fi

spawn_chengc() {
  "$CHENGC_SCRIPT" "$SRC" --name:"$NAME"
}

run_chengc() {
  if [ "${CODEX_BUILD_TRACE:-0}" = "1" ]; then
    "$CHENGC_SCRIPT" "$SRC" --name:"$NAME" &
    CHENGC_PID=$!
    {
      start_ts="$(date +%s)"
      last_stage=""
      last_log_ts="$start_ts"
      while kill -0 "$CHENGC_PID" 2>/dev/null; do
        stage="frontend running"
        if [ -f "$CHENG_ROOT/$NAME" ]; then
          stage="link done"
        elif [ -f "$CHENG_ROOT/${NAME}.o.stamp" ]; then
          stage="backend obj done"
        elif [ -d "$CHENG_ROOT/${NAME}.objs" ]; then
          stage="backend obj compiling"
        elif [ -f "$CHENG_ROOT/chengcache/${NAME}.o" ]; then
          stage="backend obj done"
        fi
        now_ts="$(date +%s)"
        if [ "$stage" != "$last_stage" ] || [ "$((now_ts - last_log_ts))" -ge "$TRACE_HEARTBEAT" ]; then
          stamp_path="$CHENG_ROOT/${NAME}.o.stamp"
          stamp_size="$(file_size_bytes "$stamp_path")"
          objs_dir="$CHENG_ROOT/${NAME}.objs"
          objs_count="0"
          if [ -d "$objs_dir" ]; then
            objs_count="$(find "$objs_dir" -type f -name '*.o' 2>/dev/null | wc -l | tr -d ' ')"
          fi
          elapsed="$((now_ts - start_ts))"
          echo "[cheng-codex] build stage: $stage (t+${elapsed}s, stamp=${stamp_size}B, objs=${objs_count})"
          last_stage="$stage"
          last_log_ts="$now_ts"
        fi
        sleep "$TRACE_INTERVAL"
      done
    } &
    TRACE_PID=$!
    wait "$CHENGC_PID"
    CHENGC_STATUS=$?
    kill "$TRACE_PID" 2>/dev/null || true
    wait "$TRACE_PID" 2>/dev/null || true
    return "$CHENGC_STATUS"
  fi
  spawn_chengc
}

reset_build_outputs() {
  rm -f \
    "$CHENG_ROOT/$NAME" \
    "$CHENG_ROOT/${NAME}.o" \
    "$CHENG_ROOT/${NAME}.o.stamp" \
    "$CHENG_ROOT/chengcache/${NAME}.o"
  rm -rf "$CHENG_ROOT/${NAME}.objs"
}

# Stage1 import resolution requires sources to live under the compiler repo root.
# Mirror src/ into a workspace directory under $CHENG_ROOT.
WORKSPACE_DIR="$WORKSPACE_ROOT/cheng-codex"
WORKSPACE_SRC="$WORKSPACE_DIR/src"
WORKSPACE_PKG_SRC="$WORKSPACE_DIR/cheng/codex"
mkdir -p "$WORKSPACE_ROOT"
if [ -L "$WORKSPACE_DIR" ]; then
  rm "$WORKSPACE_DIR"
fi
mkdir -p "$WORKSPACE_SRC"
mkdir -p "$WORKSPACE_PKG_SRC"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$ROOT/src/" "$WORKSPACE_SRC/"
  rsync -a --delete "$ROOT/src/" "$WORKSPACE_PKG_SRC/"
else
  rm -rf "$WORKSPACE_SRC"
  mkdir -p "$WORKSPACE_SRC"
  cp -R "$ROOT/src/" "$WORKSPACE_SRC/"
  rm -rf "$WORKSPACE_PKG_SRC"
  mkdir -p "$WORKSPACE_PKG_SRC"
  cp -R "$ROOT/src/" "$WORKSPACE_PKG_SRC/"
fi
if [ -f "$ROOT/cheng-package.toml" ]; then
  cp "$ROOT/cheng-package.toml" "$WORKSPACE_DIR/cheng-package.toml"
fi
append_pkg_root "$WORKSPACE_DIR"
SRC="$WORKSPACE_SRC/main.cheng"

cd "$CHENG_ROOT"
reset_build_outputs
run_chengc

BUILT_BIN=""
if [ -f "$CHENG_ROOT/$NAME" ]; then
  BUILT_BIN="$CHENG_ROOT/$NAME"
elif [ -f "$CHENG_ROOT/artifacts/chengc/$NAME" ]; then
  BUILT_BIN="$CHENG_ROOT/artifacts/chengc/$NAME"
fi

if [ -n "$BUILT_BIN" ] && [ -f "$BUILT_BIN" ]; then
  mkdir -p "$OUT_DIR"
  # Ensure a fresh inode: avoids macOS caching invalid code-sign state on overwrite.
  rm -f "$OUT_DIR/$OUT_NAME"
  cp "$BUILT_BIN" "$OUT_DIR/$OUT_NAME"
  # macOS can SIGKILL newly-built adhoc binaries unless explicitly re-signed.
  if [ "$(uname -s 2>/dev/null || true)" = "Darwin" ] && command -v codesign >/dev/null 2>&1; then
    codesign --force --sign - "$OUT_DIR/$OUT_NAME" >/dev/null 2>&1 || true
  fi
  echo "[cheng-codex] built: $OUT_DIR/$OUT_NAME"
fi
