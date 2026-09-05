#!/usr/bin/env python3
"""Validate that every manifest carries the same semver version and points at existing paths.

Manifests: plugin.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json,
.codex-plugin/plugin.json and pyproject.toml. A release tag is only valid when all five agree.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from collections.abc import Sequence
from pathlib import Path

from lib.repo import Layout, add_root_argument, configure_output, read_text
from lib.report import Report

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
REQUIRED_PLUGIN_FIELDS = ("name", "version", "description")
PATH_FIELDS = ("skills", "commands", "agents", "hooks")

# Paths the plugin loader finds on its own. Declaring one of these is not a harmless duplicate:
# the loader refuses the plugin outright, because the file is already loaded by convention and
# the manifest field exists to point at *additional* ones.
#
# This is the third time a manifest field has been wrong in a way nothing here noticed. An
# `agents` array validated and loaded zero. `hooks` pointing at the standard file installed
# clean, validated with --strict, reported two hooks in the component inventory, and still failed
# to load in a session on a newer release than the one this was developed against. So the rule is
# static rather than observed: a version that has not shipped yet cannot be interrogated, and the
# convention it enforces is documented.
CONVENTIONAL_PATHS = {
    "hooks": ("./hooks/hooks.json", "hooks/hooks.json"),
}


def _load_json(path: Path, report: Report) -> dict[str, object] | None:
    if not path.is_file():
        report.error("manifest/missing", "manifest file is missing", path)
        return None
    try:
        document = json.loads(read_text(path))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        report.error("manifest/unreadable", f"cannot parse JSON: {error}", path)
        return None
    if not isinstance(document, dict):
        report.error("manifest/shape", "top level must be a JSON object", path)
        return None
    return document


def _check_version(value: object, path: Path, report: Report) -> str | None:
    if not isinstance(value, str) or not value:
        report.error("manifest/version", "'version' must be a non-empty string", path)
        return None
    if not SEMVER_RE.match(value):
        report.error("manifest/version", f"'{value}' is not a semantic version", path)
        return None
    return value


def _check_paths(document: dict[str, object], root: Path, path: Path, report: Report) -> None:
    for field in PATH_FIELDS:
        value = document.get(field)
        if value is None:
            continue
        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if not isinstance(entry, str):
                report.error("manifest/path", f"'{field}' entries must be strings", path)
                continue
            if entry in CONVENTIONAL_PATHS.get(field, ()):
                report.error(
                    "manifest/conventional-path",
                    f"'{field}' points at '{entry}', which the loader already loads by "
                    "convention; declaring it makes the plugin fail to load as a duplicate. "
                    "Remove the field: the directory or file is found without it",
                    path,
                )
                continue
            target = root / entry
            if not target.exists():
                report.error(
                    "manifest/path", f"'{field}' points at '{entry}', which does not exist", path
                )


def _plugin_manifest(path: Path, root: Path, report: Report) -> tuple[str | None, str | None]:
    document = _load_json(path, report)
    if document is None:
        return None, None
    for field in REQUIRED_PLUGIN_FIELDS:
        value = document.get(field)
        if not isinstance(value, str) or not value.strip():
            report.error("manifest/required", f"'{field}' must be a non-empty string", path)
    _check_paths(document, root, path, report)
    name = document.get("name")
    return (name if isinstance(name, str) else None), _check_version(
        document.get("version"), path, report
    )


def _description(document: dict[str, object]) -> str | None:
    value = document.get("description")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _collect_descriptions(path: Path, root: Path, into: dict[str, str], report: Report) -> None:
    """Record every description this manifest holds, keyed by where it was found.

    A marketplace carries two: its own, and the one on the plugin it lists. Both describe the same
    package, so both belong in the comparison.
    """
    if not path.is_file():
        return
    document = _load_json(path, report)
    if not isinstance(document, dict):
        return
    where = path.relative_to(root).as_posix()
    described = _description(document)
    if described:
        into[where] = described
    plugins = document.get("plugins")
    if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict):
        nested = _description(plugins[0])
        if nested:
            into[f"{where}#plugins[0]"] = nested


def _marketplace_manifest(path: Path, root: Path, report: Report) -> tuple[str | None, str | None]:
    document = _load_json(path, report)
    if document is None:
        return None, None
    if not isinstance(document.get("name"), str) or not document["name"]:
        report.error("manifest/required", "'name' must be a non-empty string", path)
    plugins = document.get("plugins")
    if not isinstance(plugins, list) or not plugins or not isinstance(plugins[0], dict):
        report.error("manifest/shape", "'plugins' must be a non-empty list of objects", path)
        return None, None
    if len(plugins) > 1:
        report.warning("manifest/shape", "this marketplace is expected to list one plugin", path)
    plugin = plugins[0]
    source = plugin.get("source")
    if isinstance(source, str):
        if not (root / source).is_dir():
            report.error("manifest/path", f"plugin source '{source}' does not exist", path)
    elif not isinstance(source, dict):
        report.error("manifest/shape", "plugin 'source' must be a path or an object", path)
    name = plugin.get("name")
    return (name if isinstance(name, str) else None), _check_version(
        plugin.get("version"), path, report
    )


def _pyproject_version(path: Path, report: Report) -> str | None:
    if not path.is_file():
        report.error("manifest/missing", "pyproject.toml is missing", path)
        return None
    try:
        document = tomllib.loads(read_text(path))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        report.error("manifest/unreadable", f"cannot parse TOML: {error}", path)
        return None
    project = document.get("project")
    if not isinstance(project, dict):
        report.error("manifest/shape", "[project] table is missing", path)
        return None
    return _check_version(project.get("version"), path, report)


def validate(layout: Layout) -> Report:
    """Validate manifest agreement."""
    report = Report("validate-versions")
    root = layout.root
    versions: dict[Path, str] = {}
    names: dict[Path, str] = {}
    # Four fields hold the same sentence and an edit reached four of them once, which is a drift
    # nothing here could see: the required check only asks that a description exists.
    descriptions: dict[str, str] = {}

    for path in (
        root / "plugin.json",
        root / ".claude-plugin" / "plugin.json",
        root / ".codex-plugin" / "plugin.json",
    ):
        report.checked += 1
        name, version = _plugin_manifest(path, root, report)
        if name:
            names[path] = name
        if version:
            versions[path] = version
        _collect_descriptions(path, root, descriptions, report)

    marketplace = root / ".claude-plugin" / "marketplace.json"
    report.checked += 1
    _collect_descriptions(marketplace, root, descriptions, report)
    name, version = _marketplace_manifest(marketplace, root, report)
    if name:
        names[marketplace] = name
    if version:
        versions[marketplace] = version

    pyproject = root / "pyproject.toml"
    report.checked += 1
    version = _pyproject_version(pyproject, report)
    if version:
        versions[pyproject] = version

    if len(set(versions.values())) > 1:
        listing = ", ".join(
            f"{path.relative_to(root).as_posix()}={value}"
            for path, value in sorted(versions.items())
        )
        report.error("manifest/version-mismatch", f"versions differ: {listing}")
    report.checked += 1
    if len(set(descriptions.values())) > 1:
        listing = ", ".join(
            f"{where} ({len(value)} chars)" for where, value in sorted(descriptions.items())
        )
        report.error(
            "manifest/description-mismatch",
            "every manifest describes the same package, so the description has to be the same "
            f"sentence in all of them; they differ: {listing}",
        )
    if len(set(names.values())) > 1:
        listing = ", ".join(
            f"{path.relative_to(root).as_posix()}={value}" for path, value in sorted(names.items())
        )
        report.error("manifest/name-mismatch", f"plugin names differ: {listing}")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    add_root_argument(parser)
    args = parser.parse_args(argv)
    layout = Layout(args.root.resolve())
    report = validate(layout)
    print(report.render(layout.root))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
