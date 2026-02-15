#!/usr/bin/env python3
"""Hard gate for codex-rs -> cheng-codex 1:1 rewrite completeness.

This gate is intentionally strict and fails fast when rewrite coverage drifts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
from typing import Any


REQUIRED_BEHAVIOR_IDS = {
    "arg0-argv0-dispatch",
    "arg0-hidden-apply-patch-arg1",
    "arg0-root-hidden-command-surface",
    "arg0-apply-patch-standalone-usage",
    "arg0-dotenv-filter",
    "arg0-path-helper-lifecycle",
    "arg0-windows-helper-hidden-arg",
    "hooks-after-agent-legacy-notify",
    "hooks-after-tool-use-payload",
    "cli-root-help-and-version",
    "cli-help-subcommand-routing",
    "cli-error-exit-codes",
    "exec-review-surface",
    "resume-fork-selection",
    "auth-features-surface",
    "app-server-protocol-generation",
    "tui-entry-surface",
    "plan-mode-runtime",
    "request-user-input-plan-mode",
    "execpolicy-sandbox-matrix",
    "mcp-lifecycle",
    "cloud-proxy-relay",
}

REQUIRED_DOMAINS = {
    "arg0",
    "hooks",
    "cli",
    "exec-review",
    "resume-fork",
    "auth-config",
    "app-server",
    "sandbox-execpolicy",
    "mcp",
    "cloud-proxy-relay",
    "tui",
}

BASELINE_COMMIT = "ebe359b8"

REQUIRED_SOURCE_SNIPPETS = {
    "src/config.cheng": ["return os.joinPath(home, \".codex\")"],
    "src/auth_store.cheng": ["return os.joinPath(os.joinPath(home, \".codex\"), \"login.log\")"],
    "src/main.cheng": [
        "fn collectArgsFromCmdline(): str[] =",
        "let total: int32 = cmdline.paramCount()",
        "let rawArgs = collectArgsFromCmdline()",
        "if len(envHome) > 0:",
        "if ! os.dirExists(home):",
        "WARNING: proceeding, even though we could not update PATH",
    ],
}

FORBIDDEN_SOURCE_SNIPPETS = {
    "src/config.cheng": [".codex-cheng"],
    "src/auth_store.cheng": [".codex-cheng"],
    "src/sandbox_runner.cheng": [".codex-cheng"],
    "src/main.cheng": [
        "__cheng_setCmdLine(",
        "fn main(argc:",
        "argv: str*",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hard gate for 1:1 rewrite completeness")
    parser.add_argument("--cheng-root", default=".", help="Path to cheng-codex root")
    parser.add_argument(
        "--parity-manifest",
        default="tooling/parity/parity_manifest.yaml",
        help="crate-level parity manifest path",
    )
    parser.add_argument(
        "--behavior-manifest",
        default="tooling/parity/behavior_manifest.yaml",
        help="behavior-level parity manifest path",
    )
    parser.add_argument(
        "--scenarios-dir",
        default="tooling/parity/scenarios",
        help="scenario directory",
    )
    parser.add_argument(
        "--coverage-table",
        default="tooling/parity/coverage_table.md",
        help="coverage summary markdown",
    )
    parser.add_argument(
        "--out-json",
        default="build/parity/hard_gate_report.json",
        help="output report json",
    )
    parser.add_argument(
        "--out-txt",
        default="build/parity/hard_gate_report.txt",
        help="output report txt",
    )
    return parser.parse_args()


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object json: {path}")
    return data


def parse_section_metrics(md: str, section_title: str) -> dict[str, int]:
    section_pattern = re.compile(
        rf"^##\s+{re.escape(section_title)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    section_match = section_pattern.search(md)
    if not section_match:
        return {}

    section = section_match.group(1)
    metric_pattern = re.compile(r"^\|\s*([A-Za-z0-9_-]+)\s*\|\s*([0-9]+)\s*\|\s*$", re.MULTILINE)
    metrics: dict[str, int] = {}
    for key, value in metric_pattern.findall(section):
        metrics[key] = int(value)
    return metrics


def discover_scenario_refs(scenarios_dir: Path) -> set[str]:
    refs: set[str] = set()
    for path in sorted(scenarios_dir.glob("*.yaml")):
        doc = load_json_file(path)
        cases = doc.get("cases", [])
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, dict):
                continue
            case_id = str(case.get("id", "")).strip()
            if not case_id:
                continue
            refs.add(f"tooling/parity/scenarios/{path.name}::{case_id}")
    return refs


def validate(
    parity: dict[str, Any],
    behavior: dict[str, Any],
    scenario_refs: set[str],
    coverage_md: str,
    cheng_root: Path,
) -> list[str]:
    failures: list[str] = []

    parity_summary = parity.get("summary", {})
    total_crates = int(parity_summary.get("total_crates", 0))
    implemented_crates = int(parity_summary.get("implemented", 0))
    partial_crates = int(parity_summary.get("partial", 0))
    missing_crates = int(parity_summary.get("missing", 0))
    crates = parity.get("crates", [])
    if not isinstance(crates, list):
        failures.append("parity_manifest.crates must be a list")
        crates = []

    if total_crates <= 0:
        failures.append("parity_manifest total_crates must be > 0")
    if implemented_crates != total_crates:
        failures.append(
            f"parity_manifest implemented mismatch: implemented={implemented_crates} total={total_crates}"
        )
    if partial_crates != 0:
        failures.append(f"parity_manifest partial must be 0, got {partial_crates}")
    if missing_crates != 0:
        failures.append(f"parity_manifest missing must be 0, got {missing_crates}")
    if len(crates) != total_crates:
        failures.append(f"parity_manifest crate count mismatch: len(crates)={len(crates)} total={total_crates}")

    for idx, crate in enumerate(crates):
        if not isinstance(crate, dict):
            failures.append(f"crate[{idx}] is not an object")
            continue
        crate_name = str(crate.get("crate", f"#{idx}"))
        status = str(crate.get("status", "")).strip()
        if status != "implemented":
            failures.append(f"crate {crate_name} status must be implemented, got {status!r}")
        mapped = crate.get("mapped_modules", [])
        if not isinstance(mapped, list) or len(mapped) == 0:
            failures.append(f"crate {crate_name} mapped_modules must be non-empty")
        else:
            for mod in mapped:
                if not isinstance(mod, dict):
                    failures.append(f"crate {crate_name} contains non-object mapped module")
                    continue
                if not bool(mod.get("exists", False)):
                    failures.append(
                        f"crate {crate_name} mapped module missing: {mod.get('path', '<unknown>')}"
                    )

    behavior_summary = behavior.get("summary", {})
    total_behaviors = int(behavior_summary.get("total_behaviors", 0))
    implemented_behaviors = int(behavior_summary.get("implemented", 0))
    scenarized_behaviors = int(behavior_summary.get("scenarized", 0))
    behaviors = behavior.get("behaviors", [])
    if not isinstance(behaviors, list):
        failures.append("behavior_manifest.behaviors must be a list")
        behaviors = []

    baseline = behavior.get("baseline", {})
    commit = str(baseline.get("commit", "")).strip()
    if commit != BASELINE_COMMIT:
        failures.append(f"behavior_manifest baseline commit must be {BASELINE_COMMIT}, got {commit!r}")

    if total_behaviors <= 0:
        failures.append("behavior_manifest total_behaviors must be > 0")
    if implemented_behaviors != total_behaviors:
        failures.append(
            f"behavior_manifest implemented mismatch: implemented={implemented_behaviors} total={total_behaviors}"
        )
    if scenarized_behaviors != total_behaviors:
        failures.append(
            f"behavior_manifest scenarized mismatch: scenarized={scenarized_behaviors} total={total_behaviors}"
        )
    if len(behaviors) != total_behaviors:
        failures.append(
            f"behavior_manifest behavior count mismatch: len(behaviors)={len(behaviors)} total={total_behaviors}"
        )

    seen_ids: set[str] = set()
    seen_domains: set[str] = set()
    for idx, row in enumerate(behaviors):
        if not isinstance(row, dict):
            failures.append(f"behavior[{idx}] is not an object")
            continue
        behavior_id = str(row.get("id", "")).strip()
        domain = str(row.get("domain", "")).strip()
        status = str(row.get("status", "")).strip()
        if not behavior_id:
            failures.append(f"behavior[{idx}] id is empty")
            continue
        if behavior_id in seen_ids:
            failures.append(f"duplicate behavior id: {behavior_id}")
        seen_ids.add(behavior_id)
        seen_domains.add(domain)

        if status != "implemented":
            failures.append(f"behavior {behavior_id} status must be implemented, got {status!r}")

        cheng_modules = row.get("cheng_modules", [])
        if not isinstance(cheng_modules, list) or len(cheng_modules) == 0:
            failures.append(f"behavior {behavior_id} cheng_modules must be non-empty")

        source_refs = row.get("source_refs", [])
        if not isinstance(source_refs, list) or len(source_refs) == 0:
            failures.append(f"behavior {behavior_id} source_refs must be non-empty")

        refs = row.get("scenario_refs", [])
        if not isinstance(refs, list) or len(refs) == 0:
            failures.append(f"behavior {behavior_id} scenario_refs must be non-empty")
        else:
            for ref in refs:
                ref_text = str(ref).strip()
                if ref_text not in scenario_refs:
                    failures.append(f"behavior {behavior_id} scenario ref missing: {ref_text}")

    missing_required_ids = sorted(REQUIRED_BEHAVIOR_IDS - seen_ids)
    if missing_required_ids:
        failures.append(
            "missing required behavior ids: " + ", ".join(missing_required_ids)
        )

    missing_required_domains = sorted(REQUIRED_DOMAINS - seen_domains)
    if missing_required_domains:
        failures.append(
            "missing required behavior domains: " + ", ".join(missing_required_domains)
        )

    crate_metrics = parse_section_metrics(coverage_md, "Crate View")
    behavior_metrics = parse_section_metrics(coverage_md, "Behavior View")

    table_total_crates = crate_metrics.get("total_crates")
    table_implemented_crates = crate_metrics.get("implemented")
    table_partial_crates = crate_metrics.get("partial")
    table_missing_crates = crate_metrics.get("missing")
    table_total_behaviors = behavior_metrics.get("total_behaviors")
    table_implemented_behaviors = behavior_metrics.get("implemented")
    table_scenarized_behaviors = behavior_metrics.get("scenarized")

    if table_total_crates is None:
        failures.append("coverage_table missing metric: total_crates")
    elif table_total_crates != total_crates:
        failures.append(
            f"coverage_table total_crates mismatch: table={table_total_crates} manifest={total_crates}"
        )
    if table_implemented_crates is None:
        failures.append("coverage_table missing metric: implemented (crate view)")
    elif table_implemented_crates != implemented_crates:
        failures.append(
            "coverage_table implemented(crates) mismatch: "
            f"table={table_implemented_crates} manifest={implemented_crates}"
        )
    if table_partial_crates is None:
        failures.append("coverage_table missing metric: partial (crate view)")
    elif table_partial_crates != partial_crates:
        failures.append(
            f"coverage_table partial(crates) mismatch: table={table_partial_crates} manifest={partial_crates}"
        )
    if table_missing_crates is None:
        failures.append("coverage_table missing metric: missing (crate view)")
    elif table_missing_crates != missing_crates:
        failures.append(
            f"coverage_table missing(crates) mismatch: table={table_missing_crates} manifest={missing_crates}"
        )
    if table_total_behaviors is None:
        failures.append("coverage_table missing metric: total_behaviors")
    elif table_total_behaviors != total_behaviors:
        failures.append(
            f"coverage_table total_behaviors mismatch: table={table_total_behaviors} manifest={total_behaviors}"
        )
    if table_implemented_behaviors is None:
        failures.append("coverage_table missing metric: implemented (behavior view)")
    elif table_implemented_behaviors != implemented_behaviors:
        failures.append(
            "coverage_table implemented(behaviors) mismatch: "
            f"table={table_implemented_behaviors} manifest={implemented_behaviors}"
        )
    if table_scenarized_behaviors is None:
        failures.append("coverage_table missing metric: scenarized (behavior view)")
    elif table_scenarized_behaviors != scenarized_behaviors:
        failures.append(
            "coverage_table scenarized(behaviors) mismatch: "
            f"table={table_scenarized_behaviors} manifest={scenarized_behaviors}"
        )

    for rel, needles in REQUIRED_SOURCE_SNIPPETS.items():
        file_path = (cheng_root / rel).resolve()
        if not file_path.exists():
            failures.append(f"required source file missing: {rel}")
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                failures.append(f"required source snippet missing in {rel}: {needle!r}")

    for rel, needles in FORBIDDEN_SOURCE_SNIPPETS.items():
        file_path = (cheng_root / rel).resolve()
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle in text:
                failures.append(f"forbidden source snippet present in {rel}: {needle!r}")

    return failures


def main() -> int:
    args = parse_args()
    cheng_root = Path(args.cheng_root).resolve()

    parity_path = Path(args.parity_manifest)
    if not parity_path.is_absolute():
        parity_path = cheng_root / parity_path

    behavior_path = Path(args.behavior_manifest)
    if not behavior_path.is_absolute():
        behavior_path = cheng_root / behavior_path

    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = cheng_root / scenarios_dir

    coverage_path = Path(args.coverage_table)
    if not coverage_path.is_absolute():
        coverage_path = cheng_root / coverage_path

    out_json = Path(args.out_json)
    if not out_json.is_absolute():
        out_json = cheng_root / out_json
    out_txt = Path(args.out_txt)
    if not out_txt.is_absolute():
        out_txt = cheng_root / out_txt

    parity = load_json_file(parity_path)
    behavior = load_json_file(behavior_path)
    if not coverage_path.exists():
        raise FileNotFoundError(f"missing file: {coverage_path}")
    coverage_md = coverage_path.read_text(encoding="utf-8")
    scenario_refs = discover_scenario_refs(scenarios_dir)

    failures = validate(parity, behavior, scenario_refs, coverage_md, cheng_root)
    status = "pass" if not failures else "fail"

    report = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "cheng_root": str(cheng_root),
        "parity_manifest": str(parity_path),
        "behavior_manifest": str(behavior_path),
        "scenarios_dir": str(scenarios_dir),
        "coverage_table": str(coverage_path),
        "failure_count": len(failures),
        "failures": failures,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "Rewrite hard gate report",
        f"- status: {status}",
        f"- failure_count: {len(failures)}",
    ]
    for failure in failures:
        lines.append(f"  - {failure}")
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(out_json))
    print(str(out_txt))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
