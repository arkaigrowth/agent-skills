#!/usr/bin/env python3
"""Audit and register lifecycle metadata for local dependency patches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any


TRANSPILATION_HINTS = (
    "/dist/",
    "/build/",
    "/umd/",
    ".min.js",
    ".min.css",
    ".bundle.js",
    ".bundle.css",
    ".cjs",
    "/es5/",
)


@dataclass
class PatchRecord:
    patch_file: Path
    key: str
    changed_lines: int
    touched_paths: list[str]
    touches_transpiled_output: bool
    is_dev_only: bool


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def relative_to_repo(path: Path, repo: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def load_package_json(repo: Path) -> dict[str, Any]:
    package_json = repo / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = load_json(package_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid package.json: {exc}") from exc
    return data if isinstance(data, dict) else {}


def detect_package_manager(repo: Path, package_json: dict[str, Any]) -> tuple[str, list[str]]:
    markers: list[str] = []

    if (repo / "bun.lock").exists() or (repo / "bun.lockb").exists():
        markers.append("bun")
    if (repo / "pnpm-lock.yaml").exists():
        markers.append("pnpm")
    if (repo / "yarn.lock").exists():
        if (repo / ".yarnrc.yml").exists():
            markers.append("yarn-berry")
        else:
            markers.append("yarn-classic")
    if (repo / "package-lock.json").exists() or (repo / "npm-shrinkwrap.json").exists():
        markers.append("npm")

    package_manager = str(package_json.get("packageManager", "")).strip()
    if package_manager.startswith("pnpm@") and "pnpm" not in markers:
        markers.append("pnpm")
    if package_manager.startswith("yarn@"):
        major = package_manager.split("@", 1)[1].split(".", 1)[0]
        inferred = "yarn-berry" if major.isdigit() and int(major) >= 2 else "yarn-classic"
        if inferred not in markers:
            markers.append(inferred)
    if package_manager.startswith("bun@") and "bun" not in markers:
        markers.append("bun")
    if package_manager.startswith("npm@") and "npm" not in markers:
        markers.append("npm")

    unique_markers = sorted(set(markers))
    if not unique_markers:
        return "unknown", []
    if len(unique_markers) > 1:
        return "ambiguous", unique_markers
    return unique_markers[0], unique_markers


def recommended_patch_system(manager: str) -> str:
    if manager in {"npm", "yarn-classic"}:
        return "patch-package"
    if manager == "bun":
        return "bun-native"
    if manager == "pnpm":
        return "pnpm-native"
    if manager == "yarn-berry":
        return "yarn-native"
    return "unknown"


def list_patch_files(repo: Path) -> list[Path]:
    patches_dir = repo / "patches"
    if not patches_dir.exists():
        return []
    return sorted(path for path in patches_dir.glob("*.patch") if path.is_file())


def parse_patch_file(path: Path, repo: Path) -> PatchRecord:
    touched_paths: list[str] = []
    changed_lines = 0

    for raw_line in path.read_text(errors="replace").splitlines():
        if raw_line.startswith(("--- ", "+++ ")):
            candidate = raw_line[4:].strip()
            if candidate in {"/dev/null", "a/dev/null", "b/dev/null"}:
                continue
            candidate = re.sub(r"^[ab]/", "", candidate)
            touched_paths.append(candidate)
            continue
        if raw_line.startswith(("+++", "---", "@@")):
            continue
        if raw_line.startswith("+") or raw_line.startswith("-"):
            changed_lines += 1

    lowered_paths = [item.lower() for item in touched_paths]
    touches_transpiled_output = any(
        hint in candidate for hint in TRANSPILATION_HINTS for candidate in lowered_paths
    )

    return PatchRecord(
        patch_file=path,
        key=path.stem,
        changed_lines=changed_lines,
        touched_paths=touched_paths,
        touches_transpiled_output=touches_transpiled_output,
        is_dev_only=path.name.endswith(".dev.patch"),
    )


def metadata_paths(repo: Path) -> tuple[Path, Path]:
    patches_dir = repo / "patches"
    return patches_dir / ".patch-metadata.json", patches_dir / "README.md"


def load_metadata(repo: Path) -> dict[str, Any]:
    metadata_path, _ = metadata_paths(repo)
    if not metadata_path.exists():
        return {"version": 1, "patches": {}}
    try:
        payload = load_json(metadata_path)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid metadata file {metadata_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid metadata file {metadata_path}: expected an object")
    payload.setdefault("version", 1)
    payload.setdefault("patches", {})
    if not isinstance(payload["patches"], dict):
        raise SystemExit(f"Invalid metadata file {metadata_path}: 'patches' must be an object")
    return payload


def render_readme(repo: Path, metadata: dict[str, Any], patch_records: list[PatchRecord]) -> str:
    patch_index = {record.key: record for record in patch_records}

    lines = [
        "# Local Dependency Patches",
        "",
        "Generated by `scripts/patch_registry.py`.",
        "",
        "Every patch in this folder should have:",
        "",
        "- a small, reviewable diff",
        "- an owner",
        "- an upstream link when available",
        "- a concrete removal condition",
        "",
        "| Patch | System | Owner | Review | Upstream | Transpiled | Reason | Removal condition |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for key in sorted(metadata.get("patches", {})):
        entry = metadata["patches"][key]
        upstream = str(entry.get("upstream_url", "")).strip() or "-"
        owner = str(entry.get("owner", "")).strip() or "-"
        review_date = str(entry.get("review_date", "")).strip() or "-"
        system = str(entry.get("patch_system", "")).strip() or "-"
        reason = str(entry.get("reason", "")).replace("|", "/").strip() or "-"
        removal = str(entry.get("removal_condition", "")).replace("|", "/").strip() or "-"
        transpiled = "yes" if bool(entry.get("touches_transpiled_output")) else "no"
        if key not in patch_index:
            transpiled = "missing patch"
        lines.append(
            f"| `{key}` | `{system}` | `{owner}` | `{review_date}` | {upstream} | {transpiled} | {reason} | {removal} |"
        )

    if not metadata.get("patches"):
        lines.append("| - | - | - | - | - | - | - | - |")

    return "\n".join(lines) + "\n"


def cache_inputs(repo: Path) -> list[Path]:
    candidates = [
        repo / "package.json",
        repo / "package-lock.json",
        repo / "npm-shrinkwrap.json",
        repo / "bun.lock",
        repo / "bun.lockb",
        repo / "yarn.lock",
        repo / ".yarnrc.yml",
        repo / "pnpm-lock.yaml",
        repo / "pnpm-workspace.yaml",
    ]
    candidates.extend(list_patch_files(repo))
    return [path for path in candidates if path.exists() and path.is_file()]


def compute_cache_key(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(cache_inputs(repo)):
        digest.update(relative_to_repo(path, repo).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def audit_repo(repo: Path, strict: bool) -> int:
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")

    package_json = load_package_json(repo)
    manager, markers = detect_package_manager(repo, package_json)
    recommendation = recommended_patch_system(manager)
    patch_files = list_patch_files(repo)
    patch_records = [parse_patch_file(path, repo) for path in patch_files]
    metadata_path, readme_path = metadata_paths(repo)
    metadata = load_metadata(repo) if metadata_path.exists() else {"version": 1, "patches": {}}

    deps = package_json.get("dependencies", {})
    dev_deps = package_json.get("devDependencies", {})
    all_deps = {}
    if isinstance(deps, dict):
        all_deps.update(deps)
    if isinstance(dev_deps, dict):
        all_deps.update(dev_deps)

    scripts = package_json.get("scripts", {}) if isinstance(package_json.get("scripts", {}), dict) else {}
    postinstall = str(scripts.get("postinstall", "")).strip()

    fatal_issues: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if manager == "ambiguous":
        fatal_issues.append(f"Multiple package-manager signals detected: {', '.join(markers)}")
    if manager == "unknown":
        warnings.append("Could not determine the repo package manager from lockfiles or package.json.")
    if patch_files and recommendation == "unknown":
        fatal_issues.append("Patch files exist but the repo package manager could not be determined.")

    if patch_files and recommendation == "patch-package":
        if "patch-package" not in all_deps:
            warnings.append("Patch files exist but patch-package is not present in dependencies/devDependencies.")
        if "patch-package" not in postinstall:
            warnings.append("Patch files exist but package.json postinstall does not invoke patch-package.")
        if manager == "yarn-classic" and "patch-package" in postinstall and "postinstall-postinstall" not in all_deps:
            notes.append("Yarn 1 detected: consider postinstall-postinstall so yarn remove does not skip patch reapplication.")

    if patch_files and recommendation in {"bun-native", "pnpm-native", "yarn-native"} and "patch-package" in all_deps:
        warnings.append(
            "Repo appears to use a native patch-capable package manager, but patch-package is installed. Prefer native patching unless this repo deliberately standardized on patch-package."
        )

    metadata_keys = set(metadata.get("patches", {}).keys())
    patch_keys = {record.key for record in patch_records}

    if patch_files and not metadata_path.exists():
        warnings.append("Patch files exist but patches/.patch-metadata.json is missing.")
    if patch_files and not readme_path.exists():
        warnings.append("Patch files exist but patches/README.md is missing.")

    missing_metadata = sorted(patch_keys - metadata_keys)
    orphan_metadata = sorted(metadata_keys - patch_keys)
    for key in missing_metadata:
        warnings.append(f"Patch file {key}.patch has no metadata entry.")
    for key in orphan_metadata:
        warnings.append(f"Metadata entry {key} has no corresponding patch file.")

    for record in patch_records:
        if record.touches_transpiled_output:
            warnings.append(
                f"Patch {record.patch_file.name} likely edits transpiled or bundled output: {', '.join(record.touched_paths[:3])}"
            )

    print(f"repo: {repo}")
    print(f"package_manager: {manager}")
    print(f"recommended_patch_system: {recommendation}")
    print(f"patch_count: {len(patch_records)}")
    print(f"metadata_file: {'present' if metadata_path.exists() else 'missing'}")
    print(f"readme_file: {'present' if readme_path.exists() else 'missing'}")
    print(f"patch_package_dependency: {'present' if 'patch-package' in all_deps else 'missing'}")
    print(f"postinstall: {postinstall or '(none)'}")

    if patch_records:
        print("patches:")
        for record in patch_records:
            status = "transpiled=yes" if record.touches_transpiled_output else "transpiled=no"
            print(f"  - {record.patch_file.name} | lines={record.changed_lines} | {status}")

    if notes:
        print("notes:")
        for note in notes:
            print(f"  - {note}")

    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("warnings: none")

    cache_key = compute_cache_key(repo)
    print(f"cache_key: {cache_key}")

    if fatal_issues:
        print("fatal_issues:")
        for issue in fatal_issues:
            print(f"  - {issue}")
    else:
        print("fatal_issues: none")

    if fatal_issues:
        return 1
    if strict and warnings:
        return 1
    return 0


def ensure_patches_dir(repo: Path) -> Path:
    patches_dir = repo / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    return patches_dir


def register_patch(
    repo: Path,
    patch_file_arg: str,
    reason: str,
    removal_condition: str,
    owner: str,
    upstream_url: str,
    upstream_status: str,
    review_date: str | None,
    notes: str,
    patch_system: str | None,
    ai_assisted: bool,
) -> int:
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")

    ensure_patches_dir(repo)
    patch_file = Path(patch_file_arg)
    if not patch_file.is_absolute():
        patch_file = repo / patch_file
    if not patch_file.exists():
        raise SystemExit(f"Patch file does not exist: {patch_file}")

    package_json = load_package_json(repo)
    manager, _ = detect_package_manager(repo, package_json)
    record = parse_patch_file(patch_file, repo)
    metadata_path, readme_path = metadata_paths(repo)
    metadata = load_metadata(repo)
    metadata.setdefault("patches", {})

    today = date.today().isoformat()
    effective_review_date = review_date or (date.today() + timedelta(days=30)).isoformat()
    effective_patch_system = patch_system or recommended_patch_system(manager)

    existing = metadata["patches"].get(record.key, {})
    if not isinstance(existing, dict):
        existing = {}

    metadata["patches"][record.key] = {
        "patch_file": relative_to_repo(patch_file, repo),
        "package_manager": manager,
        "patch_system": effective_patch_system,
        "reason": reason,
        "owner": owner,
        "created_at": existing.get("created_at", today),
        "updated_at": today,
        "review_date": effective_review_date,
        "upstream_url": upstream_url,
        "upstream_status": upstream_status,
        "removal_condition": removal_condition,
        "ai_assisted": ai_assisted,
        "touches_transpiled_output": record.touches_transpiled_output,
        "changed_lines": record.changed_lines,
        "notes": notes,
    }

    dump_json(metadata_path, metadata)
    patch_records = [parse_patch_file(path, repo) for path in list_patch_files(repo)]
    readme_path.write_text(render_readme(repo, metadata, patch_records))

    print(f"updated metadata: {metadata_path}")
    print(f"updated readme: {readme_path}")
    print(f"registered patch: {record.key}")
    return 0


def sync_readme(repo: Path) -> int:
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")
    metadata_path, readme_path = metadata_paths(repo)
    if not metadata_path.exists():
        raise SystemExit(f"Metadata file does not exist: {metadata_path}")
    metadata = load_metadata(repo)
    patch_records = [parse_patch_file(path, repo) for path in list_patch_files(repo)]
    readme_path.write_text(render_readme(repo, metadata, patch_records))
    print(f"updated readme: {readme_path}")
    return 0


def print_cache_key(repo: Path) -> int:
    if not repo.exists():
        raise SystemExit(f"Repo does not exist: {repo}")
    print(compute_cache_key(repo))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit patch setup for a target repo.")
    audit_parser.add_argument("--repo", required=True, help="Path to the target repository.")
    audit_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when warnings are present.",
    )

    register_parser = subparsers.add_parser(
        "register",
        help="Register or update metadata for a patch file and regenerate patches/README.md.",
    )
    register_parser.add_argument("--repo", required=True, help="Path to the target repository.")
    register_parser.add_argument("--patch-file", required=True, help="Patch file path relative to the repo or absolute.")
    register_parser.add_argument("--reason", required=True, help="Why the patch exists.")
    register_parser.add_argument("--removal-condition", required=True, help="What allows the patch to be removed.")
    register_parser.add_argument("--owner", default=os.environ.get("USER", "unknown"), help="Owner of the patch.")
    register_parser.add_argument("--upstream-url", default="", help="Upstream issue, PR, or release URL.")
    register_parser.add_argument("--upstream-status", default="unknown", help="Status such as open, merged, released, or unknown.")
    register_parser.add_argument("--review-date", default=None, help="Next review date in YYYY-MM-DD. Defaults to 30 days out.")
    register_parser.add_argument("--notes", default="", help="Optional freeform notes.")
    register_parser.add_argument("--patch-system", default=None, help="Override patch system label.")
    register_parser.add_argument(
        "--human-only",
        action="store_true",
        help="Mark the patch as not AI-assisted.",
    )

    sync_parser = subparsers.add_parser(
        "sync-readme",
        help="Regenerate patches/README.md from patches/.patch-metadata.json.",
    )
    sync_parser.add_argument("--repo", required=True, help="Path to the target repository.")

    cache_parser = subparsers.add_parser(
        "cache-key",
        help="Print a stable cache key from lockfiles, package.json, and patch files.",
    )
    cache_parser.add_argument("--repo", required=True, help="Path to the target repository.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()

    if args.command == "audit":
        return audit_repo(repo, strict=args.strict)
    if args.command == "register":
        return register_patch(
            repo=repo,
            patch_file_arg=args.patch_file,
            reason=args.reason,
            removal_condition=args.removal_condition,
            owner=args.owner,
            upstream_url=args.upstream_url,
            upstream_status=args.upstream_status,
            review_date=args.review_date,
            notes=args.notes,
            patch_system=args.patch_system,
            ai_assisted=not args.human_only,
        )
    if args.command == "sync-readme":
        return sync_readme(repo)
    if args.command == "cache-key":
        return print_cache_key(repo)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
