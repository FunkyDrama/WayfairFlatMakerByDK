"""Check GitHub Releases for a newer application version."""

from dataclasses import dataclass
import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

GITHUB_REPOSITORY = "FunkyDrama/WayfairFlatMakerByDK"
LATEST_RELEASE_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
UPDATE_CHECK_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class ReleaseInfo:
    """The newest published release and its instructions page."""

    version: str
    page_url: str


def parse_version(value: str) -> tuple[int, ...]:
    """Parse a version such as ``v7.1.0`` into comparable numbers."""

    return tuple(int(part) for part in re.findall(r"\d+", value))


def is_newer_version(candidate: str, current: str) -> bool:
    """Return whether ``candidate`` is a later version than ``current``."""

    candidate_parts = parse_version(candidate)
    current_parts = parse_version(current)
    if not candidate_parts or not current_parts:
        return False
    width = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > (
        current_parts + (0,) * (width - len(current_parts))
    )


def fetch_latest_release() -> ReleaseInfo | None:
    """Return the latest GitHub release, or ``None`` when it is unavailable."""

    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "WayfairFlatMaker-update-check",
        },
    )
    try:
        with urlopen(request, timeout=UPDATE_CHECK_TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except (OSError, URLError, ValueError):
        return None

    version = data.get("tag_name")
    page_url = data.get("html_url")
    if not isinstance(version, str) or not isinstance(page_url, str):
        return None
    return ReleaseInfo(version=version.lstrip("v"), page_url=page_url)


def find_available_update(current_version: str) -> ReleaseInfo | None:
    """Return the latest release when it is newer than ``current_version``."""

    release = fetch_latest_release()
    if release is None or not is_newer_version(release.version, current_version):
        return None
    return release
