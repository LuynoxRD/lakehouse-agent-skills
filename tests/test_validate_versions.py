"""Tests for the manifest version validator."""

from __future__ import annotations

import json
import zlib

import pytest

import validate_versions
from conftest import manifest, marketplace, pyproject, write
from lib.repo import Layout


def rules(layout: Layout) -> list[str]:
    return [f.rule for f in validate_versions.validate(layout).findings]


def test_valid_manifests_are_clean(repo: Layout) -> None:
    report = validate_versions.validate(repo)
    assert report.findings == []
    assert report.checked == 6


def test_cli(repo: Layout, capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_versions.main(["--root", str(repo.root)]) == 0
    assert "validate-versions: 6 checked" in capsys.readouterr().out


def test_version_mismatch_names_files(repo: Layout) -> None:
    write(repo.root / "pyproject.toml", pyproject("0.2.0"))
    report = validate_versions.validate(repo)
    assert [f.rule for f in report.findings] == ["manifest/version-mismatch"]
    assert "pyproject.toml=0.2.0" in report.findings[0].message
    assert "plugin.json=0.1.0" in report.findings[0].message


def test_marketplace_version_and_name_participate(repo: Layout) -> None:
    write(
        repo.root / ".claude-plugin" / "marketplace.json", marketplace("0.1.1", name="other-plugin")
    )
    found = rules(repo)
    assert "manifest/version-mismatch" in found
    assert "manifest/name-mismatch" in found


@pytest.mark.parametrize("bad", ["1.0", "v1.0.0", "1.0.0.0", "", "01.0.0"])
def test_semver_is_enforced(repo: Layout, bad: str) -> None:
    write(repo.root / "plugin.json", manifest(bad))
    assert "manifest/version" in rules(repo)


def test_missing_and_unreadable_manifests(repo: Layout) -> None:
    (repo.root / ".codex-plugin" / "plugin.json").unlink()
    write(repo.root / "plugin.json", "{not json")
    found = rules(repo)
    assert "manifest/missing" in found
    assert "manifest/unreadable" in found


def test_declared_paths_must_exist(repo: Layout) -> None:
    document = json.loads((repo.root / ".claude-plugin" / "plugin.json").read_text())
    document["commands"] = ["./commands", "./.claude/commands", "./nowhere"]
    # Not the standard hooks/hooks.json: that path is refused for a different reason now, and
    # this test is about a declared path that is simply not there.
    document["hooks"] = "./hooks/absent.json"
    write(repo.root / ".claude-plugin" / "plugin.json", json.dumps(document))
    messages = [
        f.message for f in validate_versions.validate(repo).findings if f.rule == "manifest/path"
    ]
    assert len(messages) == 2
    assert any("./nowhere" in m for m in messages)
    assert any("./hooks/absent.json" in m for m in messages)


def test_marketplace_source_path_must_exist(repo: Layout) -> None:
    document = json.loads((repo.root / ".claude-plugin" / "marketplace.json").read_text())
    document["plugins"][0]["source"] = "./plugins/missing"
    write(repo.root / ".claude-plugin" / "marketplace.json", json.dumps(document))
    assert "manifest/path" in rules(repo)
    document["plugins"] = []
    write(repo.root / ".claude-plugin" / "marketplace.json", json.dumps(document))
    assert "manifest/shape" in rules(repo)


def test_required_fields(repo: Layout) -> None:
    write(
        repo.root / "plugin.json",
        json.dumps({"name": "lakehouse-agent-skills", "version": "0.1.0"}),
    )
    assert "manifest/required" in rules(repo)


def test_a_hooks_field_pointing_at_the_standard_file_is_refused(
    repo: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """Declared, it installs clean, validates strict, reports two hooks, and fails to load."""
    path = repo.root / ".claude-plugin" / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["hooks"] = "./hooks/hooks.json"
    write(path, json.dumps(document, indent=2) + "\n")

    assert validate_versions.main(["--root", str(repo.root)]) == 1
    out = capsys.readouterr().out
    assert "manifest/conventional-path" in out
    assert "already loads by convention" in out


def test_manifests_that_describe_the_package_differently_are_refused(repo: Layout) -> None:
    """Found by audit, then by the check itself.

    Six fields hold the same sentence. An edit reached five of them, and the sixth was a manifest
    neither the author nor the reviewer had listed. Nothing could see it: the existing rule only
    asked that a description exist.
    """
    manifest = repo.root / "plugin.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["description"] = "Something else entirely."
    manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")

    report = validate_versions.validate(repo)

    assert "manifest/description-mismatch" in {finding.rule for finding in report.findings}


def test_a_root_manifest_without_the_agent_plugins_schema_is_refused(repo: Layout) -> None:
    """Codex ignores such a file and Copilot reads it as a legacy plugin, personas and hooks too."""
    path = repo.root / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    del document["$schema"]
    write(path, json.dumps(document, indent=2) + "\n")

    assert rules(repo) == ["manifest/agent-plugins-schema"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("displayName", "Lakehouse Agent Skills"), ("commands", "./.claude/commands")],
)
def test_a_root_manifest_field_the_standard_does_not_have_is_refused(
    repo: Layout, field: str, value: str
) -> None:
    """Both were in the root manifest until it followed the standard."""
    path = repo.root / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document[field] = value
    write(path, json.dumps(document, indent=2) + "\n")

    assert rules(repo) == ["manifest/agent-plugins-field"]


def test_an_author_field_the_standard_does_not_have_is_refused(repo: Layout) -> None:
    path = repo.root / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["author"] = {"name": "Maintainer", "github": "maintainer"}
    write(path, json.dumps(document, indent=2) + "\n")

    assert rules(repo) == ["manifest/agent-plugins-field"]


def test_a_root_manifest_name_outside_the_standard_is_refused(repo: Layout) -> None:
    path = repo.root / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["name"] = "lakehouse--skills"
    write(path, json.dumps(document, indent=2) + "\n")

    assert "manifest/agent-plugins-name" in rules(repo)


@pytest.mark.parametrize("hooks", [None, [], ""], ids=["absent", "empty-list", "empty-string"])
def test_a_codex_manifest_that_leaves_codex_the_claude_hooks_is_refused(
    repo: Layout, hooks: object
) -> None:
    """Codex 0.164.0 loaded both Claude Code hooks from a manifest with no `hooks` field."""
    write(repo.hooks / "hooks.json", '{"hooks": {}}\n')
    path = repo.root / ".codex-plugin" / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if hooks is not None:
        document["hooks"] = hooks
    write(path, json.dumps(document, indent=2) + "\n")

    assert "manifest/codex-hooks" in rules(repo)


def test_a_codex_manifest_that_declares_no_hooks_inline_is_clean(repo: Layout) -> None:
    write(repo.hooks / "hooks.json", '{"hooks": {}}\n')
    path = repo.root / ".codex-plugin" / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["hooks"] = {"description": "None for Codex.", "hooks": {}}
    write(path, json.dumps(document, indent=2) + "\n")

    assert rules(repo) == []


def test_a_hooks_field_pointing_somewhere_else_is_allowed(
    repo: Layout, capsys: pytest.CaptureFixture[str]
) -> None:
    """The field exists to point at additional hook files, so that use must keep working."""
    write(repo.hooks / "extra.json", '{"hooks": {}}\n')
    path = repo.root / ".claude-plugin" / "plugin.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["hooks"] = "./hooks/extra.json"
    write(path, json.dumps(document, indent=2) + "\n")

    assert validate_versions.main(["--root", str(repo.root)]) == 0
    assert "conventional-path" not in capsys.readouterr().out


def png(width: int, height: int) -> bytes:
    """The signature and IHDR chunk of a PNG, which is as far as the check reads."""
    body = b"IHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    return (
        b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")
    )


def set_listing_images(repo: Layout, entry: str) -> None:
    claude = repo.root / ".claude-plugin" / "plugin.json"
    document = json.loads(claude.read_text(encoding="utf-8"))
    document["icon"] = entry
    write(claude, json.dumps(document, indent=2) + "\n")
    codex = repo.root / ".codex-plugin" / "plugin.json"
    document = json.loads(codex.read_text(encoding="utf-8"))
    document["interface"] = {"logo": entry, "composerIcon": entry}
    write(codex, json.dumps(document, indent=2) + "\n")


def test_a_square_png_listing_icon_is_clean(repo: Layout) -> None:
    (repo.root / "assets").mkdir()
    (repo.root / "assets" / "icon.png").write_bytes(png(1024, 1024))
    set_listing_images(repo, "./assets/icon.png")

    assert rules(repo) == []


@pytest.mark.parametrize(
    ("entry", "content"),
    [
        ("./assets/missing.png", None),
        ("./assets/wide.png", png(1024, 512)),
        ("./assets/icon.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>"),
        ("assets/icon.png", png(1024, 1024)),
        ("./../outside.png", png(1024, 1024)),
    ],
    ids=["missing", "not-square", "not-png", "no-dot-slash", "outside-the-plugin"],
)
def test_a_listing_icon_a_directory_would_refuse_is_reported_for_every_field(
    repo: Layout, entry: str, content: bytes | None
) -> None:
    """No loader opens these files, so without the check they fail in a directory's review."""
    if content is not None:
        target = repo.root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    set_listing_images(repo, entry)

    assert rules(repo) == ["manifest/listing-image"] * 3


def set_listing_urls(repo: Layout, url: object) -> None:
    claude = repo.root / ".claude-plugin" / "plugin.json"
    document = json.loads(claude.read_text(encoding="utf-8"))
    document.update({"documentationUrl": url, "supportUrl": url, "privacyPolicyUrl": url})
    write(claude, json.dumps(document, indent=2) + "\n")
    codex = repo.root / ".codex-plugin" / "plugin.json"
    document = json.loads(codex.read_text(encoding="utf-8"))
    document["interface"] = {"websiteURL": url, "privacyPolicyURL": url}
    write(codex, json.dumps(document, indent=2) + "\n")


def test_https_listing_links_are_clean(repo: Layout) -> None:
    set_listing_urls(
        repo, "https://github.com/LuynoxRD/lakehouse-agent-skills/blob/main/PRIVACY.md"
    )

    assert rules(repo) == []


@pytest.mark.parametrize(
    "url", ["http://example.com/privacy", "mailto:maintainer@example.com", "PRIVACY.md", 42]
)
def test_a_listing_link_that_is_not_https_is_reported_for_every_field(
    repo: Layout, url: object
) -> None:
    """Both directories take only https; an email address belongs in the author field instead."""
    set_listing_urls(repo, url)

    assert rules(repo) == ["manifest/listing-url"] * 5
