"""Upload build archives to a private Dropbox folder from the release workflow.

Usage:
    python scripts/upload_to_dropbox.py FILE [FILE ...] --folder "/Builds/v7.1.0"

Credentials come from the environment (GitHub Secrets in CI):
DROPBOX_APP_KEY, DROPBOX_APP_SECRET and DROPBOX_REFRESH_TOKEN. The Dropbox app
needs the ``files.content.write`` permission.

Builds are kept out of GitHub artifacts because, in a public repository, any
signed-in GitHub user can download those, and the builds contain the API key.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
CONTENT_API = "https://content.dropboxapi.com/2/files"
# Single uploads are capped at 150 MB, so files go up in chunks.
CHUNK_BYTES = 32 * 1024 * 1024
TIMEOUT_SECONDS = 300


def access_token() -> str:
    """Exchange the long-lived refresh token for a short-lived access token."""

    try:
        app_key = os.environ["DROPBOX_APP_KEY"]
        app_secret = os.environ["DROPBOX_APP_SECRET"]
        refresh_token = os.environ["DROPBOX_REFRESH_TOKEN"]
    except KeyError as exc:
        raise SystemExit(f"Missing Dropbox credential: {exc.args[0]}") from None

    credentials = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        ).encode(),
        headers={"Authorization": f"Basic {credentials}"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        token: str = json.load(response)["access_token"]
    return token


def call(token: str, endpoint: str, argument: dict[str, object], data: bytes) -> dict:
    """Call a Dropbox content endpoint and return its JSON reply."""

    request = urllib.request.Request(
        f"{CONTENT_API}/{endpoint}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps(argument),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise SystemExit(f"Dropbox {endpoint} failed ({exc.code}): {detail}") from None
    return json.loads(body) if body else {}


def upload(token: str, source: Path, destination: str) -> None:
    """Upload one file in chunks, overwriting any file at ``destination``."""

    size = source.stat().st_size
    with source.open("rb") as file:
        session_id = call(
            token, "upload_session/start", {"close": False}, file.read(CHUNK_BYTES)
        )["session_id"]
        while (offset := file.tell()) < size:
            chunk = file.read(CHUNK_BYTES)
            call(
                token,
                "upload_session/append_v2",
                {"cursor": {"session_id": session_id, "offset": offset}},
                chunk,
            )
        call(
            token,
            "upload_session/finish",
            {
                "cursor": {"session_id": session_id, "offset": size},
                "commit": {"path": destination, "mode": "overwrite", "mute": True},
            },
            b"",
        )
    print(f"Uploaded {source.name} ({size // (1024 * 1024)} MB) to {destination}")


def main() -> None:
    """Upload every given file into the Dropbox folder."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--folder", required=True, help="Dropbox folder path")
    args = parser.parse_args()

    folder = "/" + args.folder.strip("/")
    token = access_token()
    for source in args.files:
        if not source.is_file():
            raise SystemExit(f"Not a file: {source}")
        upload(token, source, f"{folder}/{source.name}")


if __name__ == "__main__":
    main()
