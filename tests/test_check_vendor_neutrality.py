"""Tests for the vendor-neutrality check (denylist stays outside the repository)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import check_vendor_neutrality as cvn

DENYLIST = "# comment line\n\nacmecorp\n\\bfoo[ _-]?bar\\b\nwidgets\\.example\n"


def git(root: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "clean.md").write_text("nothing to see\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "initial commit")
    return root


@pytest.fixture
def denylist(tmp_path: Path) -> Path:
    path = tmp_path / "denylist.txt"
    path.write_text(DENYLIST, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VENDOR_DENYLIST", raising=False)
    monkeypatch.delenv("VENDOR_DENYLIST_FILE", raising=False)


def test_load_patterns_skips_comments_and_is_case_insensitive() -> None:
    patterns = cvn.load_patterns(DENYLIST)
    assert len(patterns) == 3
    assert patterns[0].search("AcmeCorp rocks")
    assert patterns[1].search("the Foo-Bar tool")
    assert not patterns[1].search("foobarbaz")


def test_load_patterns_errors_never_leak_content() -> None:
    with pytest.raises(cvn.DenylistError, match="line 2 is not a valid regex"):
        cvn.load_patterns("ok\n(unclosed\n")
    with pytest.raises(cvn.DenylistError, match="no patterns"):
        cvn.load_patterns("# only comments\n\n")


def test_resolve_precedence(denylist: Path, tmp_path: Path) -> None:
    other = tmp_path / "other.txt"
    other.write_text("zzz\n", encoding="utf-8")
    assert cvn.resolve_denylist(denylist, {"VENDOR_DENYLIST": "inline"}) == DENYLIST
    assert (
        cvn.resolve_denylist(
            None, {"VENDOR_DENYLIST_FILE": str(other), "VENDOR_DENYLIST": "inline"}
        )
        == "zzz\n"
    )
    assert cvn.resolve_denylist(None, {"VENDOR_DENYLIST": "inline"}) == "inline"
    with pytest.raises(cvn.DenylistError, match="cannot read"):
        cvn.resolve_denylist(tmp_path / "missing.txt", {})


def test_scan_items_reports_pattern_index_only() -> None:
    patterns = cvn.load_patterns(DENYLIST)
    hits = cvn.scan_items([("doc.md", "fine\nmentions AcmeCorp here\nfoo_bar too")], patterns)
    assert [(h.label, h.line, h.pattern) for h in hits] == [("doc.md", 2, 1), ("doc.md", 3, 2)]


def test_tree_scan_covers_content_paths_and_untracked_files(git_repo: Path) -> None:
    (git_repo / "notes-acmecorp.md").write_text("clean body\n", encoding="utf-8")
    (git_repo / "untracked.md").write_text("see widgets.example\n", encoding="utf-8")
    (git_repo / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
    (git_repo / "ignored.md").write_text("acmecorp\n", encoding="utf-8")
    hits = cvn.scan_items(cvn.tree_items(git_repo), cvn.load_patterns(DENYLIST))
    labels = sorted(h.label for h in hits)
    assert labels == ["path notes-acmecorp.md", "untracked.md"]


def test_history_scan_covers_messages_and_refs(git_repo: Path) -> None:
    (git_repo / "clean.md").write_text("still clean\n", encoding="utf-8")
    git(git_repo, "commit", "-q", "-am", "mention AcmeCorp in a message")
    git(git_repo, "branch", "feature/foo-bar")
    hits = cvn.scan_items(cvn.history_items(git_repo), cvn.load_patterns(DENYLIST))
    kinds = sorted(h.label.split(" ")[0] for h in hits)
    assert kinds == ["commit", "ref"]


def test_staged_and_commit_message_scopes(git_repo: Path, tmp_path: Path) -> None:
    (git_repo / "staged.md").write_text("acmecorp inside\n", encoding="utf-8")
    git(git_repo, "add", "staged.md")
    hits = cvn.scan_items(cvn.staged_items(git_repo), cvn.load_patterns(DENYLIST))
    assert [h.label for h in hits] == ["staged.md"]
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("feat: add foo bar support\n", encoding="utf-8")
    hits = cvn.scan_items(cvn.commit_message_items(message), cvn.load_patterns(DENYLIST))
    assert [(h.line, h.pattern) for h in hits] == [(1, 2)]


def test_main_exit_codes_and_output(
    git_repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cvn.main(["--root", str(git_repo), "--denylist", str(denylist)]) == cvn.EXIT_CLEAN
    assert "0 hit(s): OK" in capsys.readouterr().out
    (git_repo / "bad.md").write_text("line one\nAcmeCorp appears\n", encoding="utf-8")
    assert (
        cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--tree"])
        == cvn.EXIT_FINDINGS
    )
    out = capsys.readouterr().out
    assert "bad.md:2: matches denylist pattern #1" in out
    assert "AcmeCorp" not in out
    assert (
        cvn.main(["--root", str(git_repo), "--denylist", str(denylist.with_name("none.txt"))])
        == cvn.EXIT_CONFIG
    )
    assert "cannot read" in capsys.readouterr().err


def test_a_matching_path_or_branch_is_redacted_before_it_is_printed(
    git_repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A file name or branch name that matches IS the matched text, so printing the location
    # raw would publish the protected term in a public CI log.
    (git_repo / "notes-acmecorp-migration.md").write_text("clean body\n", encoding="utf-8")
    git(git_repo, "branch", "feature/acmecorp-support")
    assert (
        cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--tree", "--history"])
        == cvn.EXIT_FINDINGS
    )
    out = capsys.readouterr().out
    assert "acmecorp" not in out.lower()
    assert "path notes-***-migration.md:1" in out
    assert "ref refs/heads/feature/***-support:1" in out


def test_redact_leaves_unmatched_text_alone() -> None:
    patterns = cvn.load_patterns(DENYLIST)
    assert cvn.redact("path docs/clean.md", patterns) == "path docs/clean.md"
    assert cvn.redact("path docs/acmecorp.md", patterns) == "path docs/***.md"


def test_root_defaults_to_the_checkout_not_the_working_directory() -> None:
    # `git ls-files` without a pathspec lists only what is below the current directory, so a
    # cwd default would silently scan a subset of the repository and still print OK.
    parser = cvn.build_parser()
    assert parser.parse_args([]).root == cvn.REPO_ROOT
    assert (cvn.REPO_ROOT / "scripts" / "check_vendor_neutrality.py").is_file()


def test_main_outside_git_is_a_config_error(
    tmp_path: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert (
        cvn.main(["--root", str(plain), "--denylist", str(denylist), "--tree"]) == cvn.EXIT_CONFIG
    )
    assert "git command failed" in capsys.readouterr().err
