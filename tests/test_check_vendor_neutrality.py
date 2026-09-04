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
    assert "0 hit(s), 0 attribution finding(s): OK" in capsys.readouterr().out
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


def test_environment_values_are_scanned_and_redacted(
    git_repo: Path,
    denylist: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pull request's title and body become the squash-merge message on the default branch.

    They are written by whoever opened the pull request, so they have to be scanned before the
    merge rather than after it, and they reach the scan through the environment because that is
    how attacker-controlled text gets into a job without ever touching a shell.
    """
    monkeypatch.setenv("PR_TITLE", "Add support for AcmeCorp exports")
    monkeypatch.setenv("PR_BRANCH", "feature/ordinary-name")

    code = cvn.main(
        ["--root", str(git_repo), "--denylist", str(denylist), "--scan-env", "PR_TITLE"]
    )

    out = capsys.readouterr().out
    assert code == cvn.EXIT_FINDINGS
    assert "env PR_TITLE:1: matches denylist pattern #1" in out
    assert "AcmeCorp" not in out
    assert "(environment)" in out

    assert (
        cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--scan-env", "PR_BRANCH"])
        == cvn.EXIT_CLEAN
    )


def test_an_unset_variable_scans_as_empty_rather_than_failing(
    git_repo: Path, denylist: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pull request with no body is ordinary; failing on it would teach people to ignore this."""
    monkeypatch.delenv("PR_BODY", raising=False)
    assert (
        cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--scan-env", "PR_BODY"])
        == cvn.EXIT_CLEAN
    )


def test_the_summary_names_what_was_actually_scanned(
    git_repo: Path,
    denylist: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reporting a scope that did not run is the failure this whole check exists to prevent."""
    monkeypatch.setenv("PR_BODY", "nothing to see")
    cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--scan-env", "PR_BODY"])
    assert "(environment)" in capsys.readouterr().out

    cvn.main(["--root", str(git_repo), "--denylist", str(denylist), "--tree"])
    assert "(tree)" in capsys.readouterr().out

    cvn.main(
        [
            "--root",
            str(git_repo),
            "--denylist",
            str(denylist),
            "--tree",
            "--history",
            "--scan-env",
            "PR_BODY",
        ]
    )
    assert "(tree, history, environment)" in capsys.readouterr().out


# Built from parts so this file does not match its own rule when the tree is scanned. A linter
# whose fixtures trip it teaches everyone to add an exception, and the exception is where the
# next real finding hides.
VENDOR = "Claude"
TRAILER = f"Co-Authored-By: {VENDOR} <noreply@example.com>"
CREDIT = f"Generated with {VENDOR} Code"
SESSION = "https://claude" + ".ai/code/session_abc123"


def attribution_reasons(text: str) -> list[str]:
    return [reason for _label, _line, reason in cvn.scan_attribution([("item", text)])]


def test_an_authorship_trailer_is_a_finding() -> None:
    """The exact line that passed the denylist scan and still signed the work over."""
    assert attribution_reasons(TRAILER) == [
        "an authorship or session trailer credits a tool or vendor"
    ]


def test_a_generated_with_line_is_a_finding() -> None:
    assert "origin of the work" in attribution_reasons(CREDIT)[0]


def test_a_vendor_session_link_is_a_finding() -> None:
    assert any("vendor session" in reason for reason in attribution_reasons(SESSION))


def test_a_session_trailer_is_a_finding() -> None:
    assert attribution_reasons(f"{VENDOR}-Session: {SESSION}")


def test_naming_a_tool_the_work_is_about_stays_legal() -> None:
    """The policy forbids credit as origin, not the name of a tool the pack targets."""
    legal = [
        "The plugin job ended at `claude plugin install`, which exits zero either way.",
        "Manifests: `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.",
        "Commands reach Claude Code and Gemini; personas and hooks are Claude Code only.",
        "Run `claude plugin details lakehouse-agent-skills` and count what loaded.",
        "A human co-author: Co-Authored-By: A Person <person@example.com>",
        # Found by the rule refusing its own commit message: a sentence about attribution that
        # happens to name the policy file is not attribution.
        "The body said the work was generated by a tool, which CLAUDE.md forbids.",
        "Written by hand, then checked against CLAUDE.md and .claude-plugin/plugin.json.",
    ]
    for line in legal:
        assert attribution_reasons(line) == [], line


def test_the_scan_reports_the_line_number() -> None:
    reported = cvn.scan_attribution([("commit abc", f"title\n\nbody\n\n{TRAILER}\n")])
    assert [(label, line) for label, line, _reason in reported] == [("commit abc", 5)]


def test_a_commit_message_with_a_trailer_fails_the_run(git_repo: Path, denylist: Path) -> None:
    """End to end, the way it would have been caught before the branch was ever pushed."""
    (git_repo / "note.md").write_text("ordinary work\n", encoding="utf-8")
    git(git_repo, "add", ".")
    git(git_repo, "commit", "-q", "-m", f"Do the work\n\n{TRAILER}")

    code = cvn.main(["--root", str(git_repo), "--history", "--denylist", str(denylist)])

    assert code == cvn.EXIT_FINDINGS


def test_a_clean_history_still_passes(git_repo: Path, denylist: Path) -> None:
    assert cvn.main(["--root", str(git_repo), "--history", "--denylist", str(denylist)]) == (
        cvn.EXIT_CLEAN
    )
