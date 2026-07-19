"""Tests for scripts/patch_registry.py.

Covers detect_package_manager across the supported package managers plus the
ambiguous and unknown cases, and parse_patch_file for path extraction, changed
line counting, transpiled-output detection, and dev-only classification.

Run from the skill root:

    python3 -m pytest -q

or with uv:

    uv run --with pytest pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import patch_registry as pr  # noqa: E402


# ---------------------------------------------------------------------------
# detect_package_manager
# ---------------------------------------------------------------------------


def test_detect_npm_from_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text("{}\n")
    manager, markers = pr.detect_package_manager(tmp_path, {})
    assert manager == "npm"
    assert markers == ["npm"]


def test_detect_npm_from_shrinkwrap(tmp_path: Path) -> None:
    (tmp_path / "npm-shrinkwrap.json").write_text("{}\n")
    manager, markers = pr.detect_package_manager(tmp_path, {})
    assert manager == "npm"


def test_detect_pnpm_from_lockfile(tmp_path: Path) -> None:
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
    manager, markers = pr.detect_package_manager(tmp_path, {})
    assert manager == "pnpm"
    assert markers == ["pnpm"]


def test_detect_yarn_classic(tmp_path: Path) -> None:
    (tmp_path / "yarn.lock").write_text("# yarn lockfile v1\n")
    manager, _ = pr.detect_package_manager(tmp_path, {})
    assert manager == "yarn-classic"


def test_detect_yarn_berry_via_yarnrc(tmp_path: Path) -> None:
    (tmp_path / "yarn.lock").write_text("__metadata:\n")
    (tmp_path / ".yarnrc.yml").write_text("nodeLinker: node-modules\n")
    manager, _ = pr.detect_package_manager(tmp_path, {})
    assert manager == "yarn-berry"


def test_detect_bun_from_lockb(tmp_path: Path) -> None:
    (tmp_path / "bun.lockb").write_bytes(b"\x00")
    manager, _ = pr.detect_package_manager(tmp_path, {})
    assert manager == "bun"


def test_detect_bun_from_text_lock(tmp_path: Path) -> None:
    (tmp_path / "bun.lock").write_text("{}\n")
    manager, _ = pr.detect_package_manager(tmp_path, {})
    assert manager == "bun"


def test_detect_ambiguous_multiple_lockfiles(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text("{}\n")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
    manager, markers = pr.detect_package_manager(tmp_path, {})
    assert manager == "ambiguous"
    assert markers == ["npm", "pnpm"]


def test_detect_unknown_when_empty(tmp_path: Path) -> None:
    manager, markers = pr.detect_package_manager(tmp_path, {})
    assert manager == "unknown"
    assert markers == []


def test_package_manager_field_pnpm(tmp_path: Path) -> None:
    manager, _ = pr.detect_package_manager(tmp_path, {"packageManager": "pnpm@9.1.0"})
    assert manager == "pnpm"


def test_package_manager_field_yarn_berry(tmp_path: Path) -> None:
    manager, _ = pr.detect_package_manager(tmp_path, {"packageManager": "yarn@3.6.4"})
    assert manager == "yarn-berry"


def test_package_manager_field_yarn_classic(tmp_path: Path) -> None:
    manager, _ = pr.detect_package_manager(tmp_path, {"packageManager": "yarn@1.22.19"})
    assert manager == "yarn-classic"


def test_lockfile_and_field_agree_stays_single(tmp_path: Path) -> None:
    # A pnpm lockfile plus a matching packageManager field must not read as ambiguous.
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
    manager, markers = pr.detect_package_manager(tmp_path, {"packageManager": "pnpm@9.1.0"})
    assert manager == "pnpm"
    assert markers == ["pnpm"]


@pytest.mark.parametrize(
    ("manager", "expected"),
    [
        ("npm", "patch-package"),
        ("yarn-classic", "patch-package"),
        ("bun", "bun-native"),
        ("pnpm", "pnpm-native"),
        ("yarn-berry", "yarn-native"),
        ("unknown", "unknown"),
    ],
)
def test_recommended_patch_system(manager: str, expected: str) -> None:
    assert pr.recommended_patch_system(manager) == expected


# ---------------------------------------------------------------------------
# parse_patch_file
# ---------------------------------------------------------------------------


def _write_patch(tmp_path: Path, name: str, body: str) -> Path:
    patch = tmp_path / name
    patch.write_text(body)
    return patch


def test_parse_patch_basic_source_edit(tmp_path: Path) -> None:
    body = (
        "--- a/node_modules/left-pad/index.js\n"
        "+++ b/node_modules/left-pad/index.js\n"
        "@@ -1,4 +1,4 @@\n"
        " module.exports = leftPad;\n"
        "-  var result = '';\n"
        "+  let result = '';\n"
    )
    patch = _write_patch(tmp_path, "left-pad+1.3.0.patch", body)
    record = pr.parse_patch_file(patch, tmp_path)

    assert record.key == "left-pad+1.3.0"
    assert record.changed_lines == 2
    assert record.touched_paths == [
        "node_modules/left-pad/index.js",
        "node_modules/left-pad/index.js",
    ]
    assert record.touches_transpiled_output is False
    assert record.is_dev_only is False


def test_parse_patch_detects_transpiled_output(tmp_path: Path) -> None:
    body = (
        "--- a/node_modules/some-lib/dist/index.min.js\n"
        "+++ b/node_modules/some-lib/dist/index.min.js\n"
        "@@ -1 +1 @@\n"
        "-!function(){bad}()\n"
        "+!function(){good}()\n"
    )
    patch = _write_patch(tmp_path, "some-lib+2.0.0.patch", body)
    record = pr.parse_patch_file(patch, tmp_path)

    assert record.touches_transpiled_output is True
    assert record.changed_lines == 2


def test_parse_patch_ignores_dev_null(tmp_path: Path) -> None:
    body = (
        "--- /dev/null\n"
        "+++ b/node_modules/new-pkg/added.js\n"
        "@@ -0,0 +1,2 @@\n"
        "+export const a = 1;\n"
        "+export const b = 2;\n"
    )
    patch = _write_patch(tmp_path, "new-pkg+1.0.0.patch", body)
    record = pr.parse_patch_file(patch, tmp_path)

    assert record.touched_paths == ["node_modules/new-pkg/added.js"]
    assert record.changed_lines == 2


def test_parse_patch_dev_only_naming(tmp_path: Path) -> None:
    body = (
        "--- a/node_modules/tool/index.js\n"
        "+++ b/node_modules/tool/index.js\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    patch = _write_patch(tmp_path, "tool+1.0.0.dev.patch", body)
    record = pr.parse_patch_file(patch, tmp_path)

    assert record.is_dev_only is True
