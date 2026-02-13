#!/usr/bin/env python3
"""Run semantic parity scenarios against codex-rs and cheng-codex.

Scenario files are `.yaml` but encoded as JSON (JSON is valid YAML).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
WS_RE = re.compile(r"\s+")
VER_RE = re.compile(r"\b\d+\.\d+(?:\.\d+)?\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run codex-rs vs cheng-codex parity scenarios")
    parser.add_argument("--cheng-root", default=".", help="Path to cheng-codex repo root")
    parser.add_argument("--codex-rs-dir", default="", help="Path to codex-rs workspace root")
    parser.add_argument("--codex-rs-bin", default="", help="Path to built codex-rs binary")
    parser.add_argument("--cheng-bin", default="", help="Path to built cheng-codex binary")
    parser.add_argument(
        "--scenarios-dir",
        default="tooling/parity/scenarios",
        help="Path to scenario directory",
    )
    parser.add_argument(
        "--out-json",
        default="build/parity/report.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--out-txt",
        default="build/parity/report.txt",
        help="Output report text path",
    )
    parser.add_argument("--timeout-sec", type=int, default=25, help="Default command timeout")
    parser.add_argument("--suite", action="append", default=[], help="Run only selected suite(s)")
    parser.add_argument("--case", action="append", default=[], help="Run only selected case id(s)")
    parser.add_argument(
        "--fail-on-skip",
        action="store_true",
        help="Treat skipped scenarios as failures",
    )
    return parser.parse_args()


def to_platform_name() -> str:
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    return "unknown"


def load_json_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, list):
        return {"cases": data, "suite": path.stem}
    if not isinstance(data, dict):
        raise ValueError(f"invalid scenario format: {path}")
    if "suite" not in data:
        data["suite"] = path.stem
    return data


def discover_scenario_files(scenarios_dir: Path) -> list[Path]:
    files = sorted(p for p in scenarios_dir.glob("*.yaml") if p.is_file())
    return files


def detect_codex_rs_dir(cheng_root: Path, explicit: str) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_dir = os.environ.get("CODEX_RS_DIR", "")
    if env_dir:
        candidates.append(Path(env_dir))

    candidates.append(cheng_root / "../../codex-lbcheng/codex-rs")
    candidates.append(cheng_root / "../codex-rs")
    candidates.append(cheng_root / "../../codex-rs")

    for candidate in candidates:
        path = candidate.resolve()
        if (path / "Cargo.toml").exists() and (path / "cli/Cargo.toml").exists():
            return path
    return None


def detect_cheng_bin(cheng_root: Path, explicit: str) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_bin = os.environ.get("CODEX_CHENG_BIN", "")
    if env_bin:
        candidates.append(Path(env_bin))
    candidates.append(cheng_root / "build/codex-cheng")

    for candidate in candidates:
        path = candidate.resolve()
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError(
        "cheng binary not found. Build first or set --cheng-bin / CODEX_CHENG_BIN"
    )


def detect_codex_rs_runner(cheng_root: Path, codex_rs_dir: Path | None, explicit_bin: str) -> tuple[list[str], Path]:
    if explicit_bin:
        path = Path(explicit_bin).resolve()
        if not (path.exists() and path.is_file() and os.access(path, os.X_OK)):
            raise FileNotFoundError(f"codex-rs binary not executable: {path}")
        return [str(path)], cheng_root

    env_bin = os.environ.get("CODEX_RS_BIN", "")
    if env_bin:
        path = Path(env_bin).resolve()
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return [str(path)], cheng_root

    if codex_rs_dir is None:
        raise FileNotFoundError(
            "codex-rs source not found. Set --codex-rs-dir or --codex-rs-bin / CODEX_RS_BIN"
        )

    debug_bin = codex_rs_dir / "target/debug/codex"
    if debug_bin.exists() and os.access(debug_bin, os.X_OK):
        return [str(debug_bin)], cheng_root

    cargo = shutil.which("cargo")
    if not cargo:
        raise FileNotFoundError("cargo not found; required to run codex-rs via cargo run")

    # Run from codex-rs workspace to resolve dependencies correctly.
    return [cargo, "run", "-q", "-p", "codex-cli", "--"], codex_rs_dir


def write_case_files(files: list[dict[str, Any]], case_tmp: Path) -> None:
    for row in files:
        rel = str(row.get("path", "")).strip()
        if not rel:
            continue
        content = str(row.get("content", ""))
        path = case_tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def render_value(value: Any, context: dict[str, str]) -> Any:
    if isinstance(value, str):
        out = value
        for key, val in context.items():
            out = out.replace("{{" + key + "}}", val)
        return out
    if isinstance(value, list):
        return [render_value(v, context) for v in value]
    if isinstance(value, dict):
        return {k: render_value(v, context) for k, v in value.items()}
    return value


def norm_text(text: str, rules: list[str]) -> str:
    out = text
    for rule in rules:
        if rule == "strip_ansi":
            out = ANSI_RE.sub("", out)
        elif rule == "canonical_bin_name":
            out = out.replace("codex-cheng", "codex")
        elif rule == "drop_versions":
            out = VER_RE.sub("<VER>", out)
        elif rule == "collapse_ws":
            out = WS_RE.sub(" ", out)
        elif rule == "trim":
            out = out.strip()
    return out


def check_contains(label: str, haystack: str, needles: list[str], failures: list[str]) -> None:
    for needle in needles:
        if needle not in haystack:
            failures.append(f"{label} missing text: {needle!r}")


def check_not_contains(label: str, haystack: str, needles: list[str], failures: list[str]) -> None:
    for needle in needles:
        if needle in haystack:
            failures.append(f"{label} must not contain: {needle!r}")


def check_regex(label: str, haystack: str, patterns: list[str], failures: list[str]) -> None:
    for pattern in patterns:
        if not re.search(pattern, haystack, re.MULTILINE):
            failures.append(f"{label} missing regex: /{pattern}/")


def platform_allowed(case: dict[str, Any], host_platform: str) -> bool:
    platforms = case.get("platforms", ["all"])
    if isinstance(platforms, str):
        platforms = [platforms]
    platforms = [str(p).lower() for p in platforms]
    return "all" in platforms or host_platform in platforms


def run_cmd(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    stdin_text: str,
    timeout_sec: int,
    argv0: str = "",
) -> dict[str, Any]:
    start = time.monotonic()
    run_cmd_args = list(cmd)
    executable = None
    if argv0 and os.name != "nt" and len(cmd) > 0:
        executable = cmd[0]
        run_cmd_args = [argv0, *cmd[1:]]
    try:
        proc = subprocess.run(
            run_cmd_args,
            cwd=str(cwd),
            env=env,
            executable=executable,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "exit_code": -124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "duration_ms": duration_ms,
        }


def merge_env(base_env: dict[str, str], extra_env: dict[str, Any]) -> dict[str, str]:
    out = dict(base_env)
    for key, value in extra_env.items():
        out[str(key)] = str(value)
    return out


def run_side_steps(
    side: str,
    case: dict[str, Any],
    base_cmd: list[str],
    base_cwd: Path,
    host_env: dict[str, str],
    default_timeout: int,
) -> dict[str, Any]:
    case_tmp = Path(tempfile.mkdtemp(prefix=f"parity-{case['id']}-{side}-"))
    home_dir = str(host_env.get("HOME", ""))
    codex_home = str(host_env.get("CODEX_HOME", ""))
    context = {
        "CASE_TMP": str(case_tmp),
        "PROJECT_ROOT": str(base_cwd),
        "HOME": home_dir,
        "CODEX_HOME": codex_home,
    }

    files = render_value(case.get("files", []), context)
    if isinstance(files, list):
        write_case_files(files, case_tmp)

    commands = case.get("steps")
    if not commands:
        commands = [case]

    step_rows: list[dict[str, Any]] = []
    combined_stdout_parts: list[str] = []
    combined_stderr_parts: list[str] = []
    last_exit = 0
    timed_out_any = False
    total_duration = 0

    for idx, step in enumerate(commands):
        step_obj = step if isinstance(step, dict) else {}
        local_context = dict(context)
        local_context["STEP_INDEX"] = str(idx)

        args_key = f"{side}_args"
        raw_args = step_obj.get(args_key, step_obj.get("args", []))
        args = render_value(raw_args, local_context)
        if not isinstance(args, list):
            args = []

        stdin_key = f"{side}_stdin"
        stdin_text = render_value(step_obj.get(stdin_key, step_obj.get("stdin", "")), local_context)
        if not isinstance(stdin_text, str):
            stdin_text = str(stdin_text)

        env_key = f"{side}_env"
        extra_env = render_value(step_obj.get(env_key, step_obj.get("env", {})), local_context)
        if not isinstance(extra_env, dict):
            extra_env = {}
        merged_env = merge_env(host_env, extra_env)
        local_context["HOME"] = str(merged_env.get("HOME", ""))
        local_context["CODEX_HOME"] = str(merged_env.get("CODEX_HOME", ""))

        cwd_raw = render_value(step_obj.get("cwd", ""), local_context)
        step_cwd = Path(cwd_raw).resolve() if cwd_raw else base_cwd

        timeout_sec = int(step_obj.get("timeout_sec", case.get("timeout_sec", default_timeout)))
        argv0_key = f"{side}_argv0"
        argv0 = render_value(step_obj.get(argv0_key, step_obj.get("argv0", "")), local_context)
        if not isinstance(argv0, str):
            argv0 = str(argv0)

        cmd = [*base_cmd, *[str(a) for a in args]]
        result = run_cmd(cmd, step_cwd, merged_env, stdin_text, timeout_sec, argv0=argv0)

        last_exit = int(result["exit_code"])
        timed_out_any = timed_out_any or bool(result["timed_out"])
        total_duration += int(result["duration_ms"])

        combined_stdout_parts.append(str(result["stdout"]))
        combined_stderr_parts.append(str(result["stderr"]))

        step_rows.append(
            {
                "index": idx,
                "cmd": cmd,
                "argv0": argv0,
                "cwd": str(step_cwd),
                "timeout_sec": timeout_sec,
                **result,
            }
        )

    return {
        "tmp_dir": str(case_tmp),
        "steps": step_rows,
        "exit_code": last_exit,
        "stdout": "".join(combined_stdout_parts),
        "stderr": "".join(combined_stderr_parts),
        "timed_out": timed_out_any,
        "duration_ms": total_duration,
        "home": home_dir,
        "codex_home": codex_home,
    }


def evaluate_single_expectations(
    prefix: str,
    result: dict[str, Any],
    expect: dict[str, Any],
    failures: list[str],
) -> None:
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))

    check_contains(f"{prefix}.stdout", stdout, [str(v) for v in expect.get("stdout_contains", [])], failures)
    check_contains(f"{prefix}.stderr", stderr, [str(v) for v in expect.get("stderr_contains", [])], failures)
    check_not_contains(
        f"{prefix}.stdout",
        stdout,
        [str(v) for v in expect.get("stdout_not_contains", [])],
        failures,
    )
    check_not_contains(
        f"{prefix}.stderr",
        stderr,
        [str(v) for v in expect.get("stderr_not_contains", [])],
        failures,
    )
    check_regex(f"{prefix}.stdout", stdout, [str(v) for v in expect.get("stdout_regex", [])], failures)
    check_regex(f"{prefix}.stderr", stderr, [str(v) for v in expect.get("stderr_regex", [])], failures)


def evaluate_case(
    case: dict[str, Any],
    baseline: dict[str, Any],
    cheng: dict[str, Any],
    cheng_root: Path,
) -> list[str]:
    failures: list[str] = []
    expect = case.get("expect", {})
    if not isinstance(expect, dict):
        expect = {}

    if case.get("source_checks"):
        for row in case.get("source_checks", []):
            if not isinstance(row, dict):
                continue
            rel = str(row.get("path", "")).strip()
            needle = str(row.get("contains", ""))
            if not rel or not needle:
                continue
            file_path = (cheng_root / rel).resolve()
            if not file_path.exists():
                failures.append(f"source check missing file: {rel}")
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if needle not in text:
                failures.append(f"source check missing text in {rel}: {needle!r}")

    if not expect.get("ignore_exit_code", False):
        if expect.get("both_nonzero", False):
            if int(baseline.get("exit_code", 0)) == 0:
                failures.append("baseline exit code must be non-zero")
            if int(cheng.get("exit_code", 0)) == 0:
                failures.append("cheng exit code must be non-zero")
        else:
            expected_exit = expect.get("exit_code", "equal")
            if isinstance(expected_exit, int):
                if int(baseline.get("exit_code", 0)) != expected_exit:
                    failures.append(
                        f"baseline exit code mismatch: expected {expected_exit}, got {baseline.get('exit_code')}"
                    )
                if int(cheng.get("exit_code", 0)) != expected_exit:
                    failures.append(
                        f"cheng exit code mismatch: expected {expected_exit}, got {cheng.get('exit_code')}"
                    )
            else:
                if int(baseline.get("exit_code", 0)) != int(cheng.get("exit_code", 0)):
                    failures.append(
                        f"exit code mismatch: baseline={baseline.get('exit_code')} cheng={cheng.get('exit_code')}"
                    )

        if "baseline_exit_code" in expect:
            v = int(expect["baseline_exit_code"])
            if int(baseline.get("exit_code", 0)) != v:
                failures.append(f"baseline exit code must be {v}")
        if "cheng_exit_code" in expect:
            v = int(expect["cheng_exit_code"])
            if int(cheng.get("exit_code", 0)) != v:
                failures.append(f"cheng exit code must be {v}")

    evaluate_single_expectations("baseline", baseline, expect, failures)
    evaluate_single_expectations("cheng", cheng, expect, failures)

    b_expect = expect.get("baseline", {})
    c_expect = expect.get("cheng", {})
    if isinstance(b_expect, dict):
        evaluate_single_expectations("baseline", baseline, b_expect, failures)
    if isinstance(c_expect, dict):
        evaluate_single_expectations("cheng", cheng, c_expect, failures)

    baseline_tmp = str(baseline.get("tmp_dir", ""))
    cheng_tmp = str(cheng.get("tmp_dir", ""))
    baseline_paths = [str(v) for v in expect.get("baseline_paths_exist", [])]
    cheng_paths = [str(v) for v in expect.get("cheng_paths_exist", [])]

    for raw in baseline_paths:
        path = Path(raw.replace("{{CASE_TMP}}", baseline_tmp))
        if not path.exists():
            failures.append(f"baseline expected path missing: {path}")
    for raw in cheng_paths:
        path = Path(raw.replace("{{CASE_TMP}}", cheng_tmp))
        if not path.exists():
            failures.append(f"cheng expected path missing: {path}")

    if expect.get("normalized_stdout_equal", False):
        rules = [str(v) for v in expect.get("normalizers", ["strip_ansi", "canonical_bin_name", "drop_versions", "collapse_ws", "trim"])]
        b = norm_text(str(baseline.get("stdout", "")), rules)
        c = norm_text(str(cheng.get("stdout", "")), rules)
        if b != c:
            failures.append("normalized stdout mismatch")

    if expect.get("normalized_stderr_equal", False):
        rules = [str(v) for v in expect.get("normalizers", ["strip_ansi", "canonical_bin_name", "drop_versions", "collapse_ws", "trim"])]
        b = norm_text(str(baseline.get("stderr", "")), rules)
        c = norm_text(str(cheng.get("stderr", "")), rules)
        if b != c:
            failures.append("normalized stderr mismatch")

    return failures


def truncate_text(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>..."


def select_case(case: dict[str, Any], suites: set[str], case_ids: set[str], suite_name: str) -> bool:
    if suites and suite_name not in suites:
        return False
    if case_ids and str(case.get("id", "")) not in case_ids:
        return False
    return True


def main() -> int:
    args = parse_args()
    cheng_root = Path(args.cheng_root).resolve()
    host_platform = to_platform_name()

    codex_rs_dir = detect_codex_rs_dir(cheng_root, args.codex_rs_dir)
    cheng_bin = detect_cheng_bin(cheng_root, args.cheng_bin)
    baseline_cmd, baseline_default_cwd = detect_codex_rs_runner(cheng_root, codex_rs_dir, args.codex_rs_bin)
    baseline_direct_bin = len(baseline_cmd) == 1 and Path(baseline_cmd[0]).exists()

    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = cheng_root / scenarios_dir
    scenario_files = discover_scenario_files(scenarios_dir)
    if not scenario_files:
        raise FileNotFoundError(f"no scenarios found in {scenarios_dir}")

    results: list[dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    skip_count = 0

    selected_suites = {s.strip() for s in args.suite if s.strip()}
    selected_cases = {c.strip() for c in args.case if c.strip()}

    for file_path in scenario_files:
        suite_doc = load_json_yaml(file_path)
        suite_name = str(suite_doc.get("suite", file_path.stem))
        cases = suite_doc.get("cases", [])
        if not isinstance(cases, list):
            continue

        for idx, raw_case in enumerate(cases):
            case = raw_case if isinstance(raw_case, dict) else {}
            case_id = str(case.get("id", f"{suite_name}-{idx}"))
            case["id"] = case_id

            if not select_case(case, selected_suites, selected_cases, suite_name):
                continue

            started = time.monotonic()
            if not platform_allowed(case, host_platform):
                status = "skip"
                reasons = [f"platform {host_platform} not in {case.get('platforms')}"]
                row = {
                    "suite": suite_name,
                    "id": case_id,
                    "description": str(case.get("description", "")),
                    "status": status,
                    "reasons": reasons,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
                results.append(row)
                skip_count += 1
                continue
            if bool(case.get("requires_direct_bin", False)) and not baseline_direct_bin:
                status = "skip"
                reasons = ["requires direct codex-rs binary (--codex-rs-bin or target/debug/codex) for argv0 scenario"]
                row = {
                    "suite": suite_name,
                    "id": case_id,
                    "description": str(case.get("description", "")),
                    "status": status,
                    "reasons": reasons,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
                results.append(row)
                skip_count += 1
                continue

            host_env = dict(os.environ)
            # Default to isolated HOME for deterministic config/auth behavior.
            temp_home = Path(tempfile.mkdtemp(prefix=f"parity-home-{case_id}-"))
            host_env["HOME"] = str(temp_home)

            baseline = run_side_steps(
                "baseline",
                case,
                baseline_cmd,
                baseline_default_cwd,
                host_env,
                args.timeout_sec,
            )
            cheng = run_side_steps(
                "cheng",
                case,
                [str(cheng_bin)],
                cheng_root,
                host_env,
                args.timeout_sec,
            )

            failures = evaluate_case(case, baseline, cheng, cheng_root)
            status = "pass" if not failures else "fail"

            row = {
                "suite": suite_name,
                "id": case_id,
                "description": str(case.get("description", "")),
                "status": status,
                "reasons": failures,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "baseline": {
                    "exit_code": baseline.get("exit_code"),
                    "timed_out": baseline.get("timed_out"),
                    "duration_ms": baseline.get("duration_ms"),
                    "stdout": truncate_text(str(baseline.get("stdout", ""))),
                    "stderr": truncate_text(str(baseline.get("stderr", ""))),
                    "steps": baseline.get("steps", []),
                },
                "cheng": {
                    "exit_code": cheng.get("exit_code"),
                    "timed_out": cheng.get("timed_out"),
                    "duration_ms": cheng.get("duration_ms"),
                    "stdout": truncate_text(str(cheng.get("stdout", ""))),
                    "stderr": truncate_text(str(cheng.get("stderr", ""))),
                    "steps": cheng.get("steps", []),
                },
            }
            results.append(row)

            if status == "pass":
                pass_count += 1
            else:
                fail_count += 1

    if args.fail_on_skip and skip_count > 0:
        fail_count += skip_count

    summary = {
        "total": len(results),
        "pass": pass_count,
        "fail": fail_count,
        "skip": skip_count,
    }

    report = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host_platform": host_platform,
        "cheng_root": str(cheng_root),
        "codex_rs_dir": str(codex_rs_dir) if codex_rs_dir else "",
        "codex_rs_cmd": baseline_cmd,
        "cheng_cmd": [str(cheng_bin)],
        "summary": summary,
        "results": results,
    }

    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = cheng_root / out_json
    out_txt = Path(args.out_txt)
    if not out_txt.is_absolute():
        out_txt = cheng_root / out_txt

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("Parity report")
    lines.append(f"- generated_at: {report['generated_at']}")
    lines.append(f"- host_platform: {host_platform}")
    lines.append(f"- total: {summary['total']}")
    lines.append(f"- pass: {summary['pass']}")
    lines.append(f"- fail: {summary['fail']}")
    lines.append(f"- skip: {summary['skip']}")
    lines.append("")
    for row in results:
        lines.append(f"[{row['status']}] {row['suite']}::{row['id']}")
        if row.get("reasons"):
            for reason in row["reasons"]:
                lines.append(f"  - {reason}")
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(out_json))
    print(str(out_txt))

    return 1 if summary["fail"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
