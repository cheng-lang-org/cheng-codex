#!/usr/bin/env python3
"""Generate parity manifest between codex-rs workspace crates and cheng-codex modules.

The output file uses JSON syntax with a `.yaml` suffix so it is valid YAML.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate parity manifest")
    parser.add_argument("--codex-rs-dir", required=True, help="Path to codex-rs workspace root")
    parser.add_argument("--cheng-root", required=True, help="Path to cheng-codex root")
    parser.add_argument(
        "--module-map",
        default="tooling/parity/module_map.yaml",
        help="Module map file (JSON-encoded YAML)",
    )
    parser.add_argument(
        "--out",
        default="tooling/parity/parity_manifest.yaml",
        help="Manifest output path",
    )
    return parser.parse_args()


def read_workspace_members(codex_rs_dir: Path) -> list[str]:
    cargo_toml = codex_rs_dir / "Cargo.toml"
    if not cargo_toml.exists():
        raise FileNotFoundError(f"missing Cargo.toml: {cargo_toml}")

    # Try tomllib first; fallback to regex so the script works on older python.
    try:
        import tomllib  # type: ignore

        data = tomllib.loads(cargo_toml.read_text(encoding="utf-8"))
        members = data.get("workspace", {}).get("members", [])
        return [str(member) for member in members]
    except Exception:
        text = cargo_toml.read_text(encoding="utf-8")
        block_match = re.search(r"members\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if not block_match:
            return []
        block = block_match.group(1)
        return re.findall(r'"([^"]+)"', block)


def count_rs_loc(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for rs in path.rglob("*.rs"):
        try:
            with rs.open("r", encoding="utf-8", errors="ignore") as fh:
                total += sum(1 for _ in fh)
        except OSError:
            continue
    return total


def count_cheng_loc(path: Path) -> int:
    total = 0
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0
    if path.is_dir():
        for cheng in path.rglob("*.cheng"):
            try:
                with cheng.open("r", encoding="utf-8", errors="ignore") as fh:
                    total += sum(1 for _ in fh)
            except OSError:
                continue
    return total


def load_module_map(cheng_root: Path, module_map_path: str) -> dict[str, Any]:
    path = Path(module_map_path)
    if not path.is_absolute():
        path = cheng_root / path
    if not path.exists():
        raise FileNotFoundError(f"missing module map: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_path(path_text: str) -> str:
    return path_text.replace("\\", "/")


def main() -> int:
    args = parse_args()
    codex_rs_dir = Path(args.codex_rs_dir).resolve()
    cheng_root = Path(args.cheng_root).resolve()
    module_map_data = load_module_map(cheng_root, args.module_map)

    mappings_raw = module_map_data.get("mappings", [])
    mapping_by_crate: dict[str, dict[str, Any]] = {}
    for row in mappings_raw:
        crate = row.get("crate", "")
        if crate:
            mapping_by_crate[crate] = row

    members = read_workspace_members(codex_rs_dir)
    crates: list[dict[str, Any]] = []
    implemented = 0
    partial = 0
    missing = 0

    for crate in members:
        crate_path = codex_rs_dir / crate
        rs_loc = count_rs_loc(crate_path)

        mapping = mapping_by_crate.get(crate)
        mapped_modules = mapping.get("cheng_modules", []) if mapping else []
        notes = mapping.get("notes", "") if mapping else ""

        module_rows: list[dict[str, Any]] = []
        existing_count = 0
        mapped_loc = 0
        for mod in mapped_modules:
            rel = normalize_path(str(mod))
            mod_path = cheng_root / rel
            exists = mod_path.exists()
            if exists:
                existing_count += 1
                mapped_loc += count_cheng_loc(mod_path)
            module_rows.append(
                {
                    "path": rel,
                    "exists": exists,
                    "loc": count_cheng_loc(mod_path) if exists else 0,
                }
            )

        if not mapped_modules:
            status = "missing"
            missing += 1
        elif existing_count == len(mapped_modules):
            status = "implemented"
            implemented += 1
        elif existing_count > 0:
            status = "partial"
            partial += 1
        else:
            status = "missing"
            missing += 1

        crates.append(
            {
                "crate": crate,
                "status": status,
                "rs_path": normalize_path(crate),
                "rs_loc": rs_loc,
                "cheng_mapped_loc": mapped_loc,
                "notes": notes,
                "mapped_modules": module_rows,
            }
        )

    output = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline": {
            "codex_rs_dir": str(codex_rs_dir),
            "cheng_root": str(cheng_root),
            "git_hint": "codex-rs baseline should be pinned by caller",
        },
        "summary": {
            "total_crates": len(crates),
            "implemented": implemented,
            "partial": partial,
            "missing": missing,
        },
        "crates": crates,
    }

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = cheng_root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
