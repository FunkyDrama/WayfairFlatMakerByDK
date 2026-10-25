"""Bump the app version in pyproject.toml, then commit and tag the release.

Usage:
    python scripts/bump_version.py [major|minor|patch] [--dry-run]
    python scripts/bump_version.py --check

Without a level, it is chosen from Conventional Commit messages since the last
tag: "type!:" or "BREAKING CHANGE" -> major, "feat:" -> minor, otherwise patch.

``project.version`` is the single source of the app version (the window title,
the update check, and the release workflow all read it). ``tool.flet.build_number``
must grow with every release, so both are bumped together. ``--check`` is the
pre-commit guard that rejects a version change without a build-number bump.
"""

import argparse
from pathlib import Path
import re
import subprocess
import tomllib

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
LEVELS = ("major", "minor", "patch")
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*args: str) -> str:
    """Run a git command and return its trimmed output."""

    result = subprocess.run(
        ["git", *args], cwd=PYPROJECT.parent, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def read_versions(text: str) -> tuple[str, int]:
    """Return ``(project.version, tool.flet.build_number)`` from pyproject text."""

    data = tomllib.loads(text)
    version = data["project"]["version"]
    build_number = data["tool"]["flet"]["build_number"]
    if not VERSION_PATTERN.match(version):
        raise SystemExit(f"Version {version!r} is not in MAJOR.MINOR.PATCH form.")
    if not isinstance(build_number, int):
        raise SystemExit("tool.flet.build_number must be a whole number.")
    return version, build_number


def detect_level() -> str:
    """Choose the bump level from commit messages since the last tag."""

    last_tag = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=PYPROJECT.parent,
        capture_output=True,
        text=True,
    ).stdout.strip()
    revision_range = f"{last_tag}..HEAD" if last_tag else "HEAD"
    messages = git("log", revision_range, "--format=%B%x00").split("\x00")
    if any(
        re.match(r"^\w+(\([^)]*\))?!:", message.strip()) or "BREAKING CHANGE" in message
        for message in messages
    ):
        return "major"
    if any(re.match(r"^feat(\([^)]*\))?:", message.strip()) for message in messages):
        return "minor"
    return "patch"


def next_version(version: str, level: str) -> str:
    """Return ``version`` raised by one ``level``."""

    match = VERSION_PATTERN.match(version)
    assert match is not None
    major, minor, patch = (int(part) for part in match.groups())
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def replace_once(text: str, pattern: str, replacement: str) -> str:
    """Replace exactly one match of ``pattern`` or stop with an error."""

    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise SystemExit(f"Could not find {pattern!r} in pyproject.toml.")
    return updated


def bump(level: str | None, dry_run: bool) -> None:
    """Bump versions, then commit and tag unless ``dry_run`` is set."""

    text = PYPROJECT.read_text(encoding="utf-8")
    version, build_number = read_versions(text)
    level = level or detect_level()
    new_version = next_version(version, level)
    new_build_number = build_number + 1

    print(
        f"{level}: {version} -> {new_version}, build {build_number} -> "
        f"{new_build_number}"
    )
    if dry_run:
        return

    if git("status", "--porcelain"):
        raise SystemExit(
            "Commit or stash your changes first: the release commit "
            "must contain only the version bump."
        )

    text = replace_once(
        text, rf'^version = "{re.escape(version)}"$', f'version = "{new_version}"'
    )
    text = replace_once(
        text, rf"^build_number = {build_number}$", f"build_number = {new_build_number}"
    )
    PYPROJECT.write_text(text, encoding="utf-8")

    tag = f"v{new_version}"
    git("add", PYPROJECT.name)
    git("commit", "-m", f"chore(release): {tag}")
    git("tag", "-a", tag, "-m", f"Release {tag}")
    print(
        f"Created commit and tag {tag}. Publish with:\n"
        "    git push origin main --follow-tags"
    )


def check() -> None:
    """Fail when the staged version changed without a build-number bump."""

    staged = git("show", f":{PYPROJECT.name}")
    try:
        committed = git("show", f"HEAD:{PYPROJECT.name}")
    except SystemExit:
        return  # first commit: nothing to compare with
    new_version, new_build = read_versions(staged)
    old_version, old_build = read_versions(committed)
    if new_version != old_version and new_build <= old_build:
        raise SystemExit(
            f"Version changed {old_version} -> {new_version} but build_number "
            f"stayed {new_build}. Use `make release` (scripts/bump_version.py), "
            "or raise tool.flet.build_number too."
        )
    if new_build != old_build and new_version == old_version:
        raise SystemExit(
            f"build_number changed {old_build} -> {new_build} without a version "
            "change. Use `make release` to bump both."
        )


def main() -> None:
    """Parse arguments and run the requested mode."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("level", nargs="?", choices=LEVELS)
    parser.add_argument("--dry-run", action="store_true", help="only print")
    parser.add_argument("--check", action="store_true", help="pre-commit guard")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        bump(args.level, args.dry_run)


if __name__ == "__main__":
    main()
