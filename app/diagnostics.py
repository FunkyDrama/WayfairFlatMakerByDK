"""Hidden diagnostic log: setup, weekly cleanup, and export for the developer.

The log lives in the per-user application data folder, never next to the
operator's spreadsheets. It starts fresh once it is older than a week (the
previous week is kept as ``app.log.1``) and is also capped by size, so it never
grows without bound. ``export_diagnostics`` zips it with system details so the
developer can ask an operator for it after a failure.
"""

import asyncio
from collections.abc import Iterator
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import sys
import threading
import time
from types import TracebackType
import zipfile

APP_FOLDER_NAME = "WayfairFlatMakerByDK"
LOGGER_NAME = "wayfair"
LOG_FILE_NAME = "app.log"
LOG_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s"
# Records when the current log was started; file mtimes change on every write.
LOG_STARTED_MARKER = ".log_started"

logger = logging.getLogger(LOGGER_NAME)


def get_logger(name: str) -> logging.Logger:
    """Return a child of the application logger, e.g. ``wayfair.export``."""

    return logger.getChild(name)


def log_directory() -> Path:
    """Return the per-user folder that holds the diagnostic log."""

    # flet build sets this to the platform application-data folder.
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        base = Path(flet_storage)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = (
            Path(local_app_data) if local_app_data else Path.home() / "AppData"
        ) / APP_FOLDER_NAME
    else:
        base = Path.home() / ".local" / "state" / APP_FOLDER_NAME
    return base / "logs"


def log_files(directory: Path) -> Iterator[Path]:
    """Yield the existing log files, newest first."""

    for name in (LOG_FILE_NAME, f"{LOG_FILE_NAME}.1"):
        path = directory / name
        if path.exists():
            yield path


def start_new_week_if_due(directory: Path) -> None:
    """Rotate the log when the current one was started over a week ago."""

    marker = directory / LOG_STARTED_MARKER
    current = directory / LOG_FILE_NAME
    try:
        started = float(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        started = None

    if started is not None and time.time() - started < LOG_MAX_AGE_SECONDS:
        return
    if started is not None and current.exists():
        current.replace(directory / f"{LOG_FILE_NAME}.1")
    marker.write_text(str(time.time()), encoding="utf-8")


class SecretRedactingFilter(logging.Filter):
    """Mask secrets, such as the Gemini API key, in every log record."""

    def __init__(self, secrets: list[str]) -> None:
        """Store the values that must never reach the log file."""

        super().__init__()
        self.secrets = [secret for secret in secrets if len(secret) >= 8]

    def filter(self, record: logging.LogRecord) -> bool:
        """Rewrite the formatted message with secrets replaced."""

        if self.secrets:
            message = record.getMessage()
            for secret in self.secrets:
                message = message.replace(secret, "***")
            record.msg, record.args = message, None
        return True


def install_exception_hooks() -> None:
    """Log uncaught exceptions from the main thread and worker threads."""

    previous_hook = sys.excepthook

    def log_uncaught(
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, traceback))
        previous_hook(exc_type, exc_value, traceback)

    def log_thread_exception(args: threading.ExceptHookArgs) -> None:
        logger.critical(
            "Uncaught exception in thread %s: %s",
            args.thread.name if args.thread else "?",
            args.exc_type.__name__,
            exc_info=args.exc_value,
        )

    sys.excepthook = log_uncaught
    threading.excepthook = log_thread_exception


def install_asyncio_exception_handler() -> None:
    """Log exceptions from background tasks that nobody awaited."""

    loop = asyncio.get_running_loop()

    def handle(loop: asyncio.AbstractEventLoop, context: dict[str, object]) -> None:
        exception = context.get("exception")
        logger.error(
            "Unhandled asyncio error: %s",
            context.get("message"),
            exc_info=exception if isinstance(exception, BaseException) else None,
        )

    loop.set_exception_handler(handle)


def setup_logging(app_version: str, secrets: list[str]) -> Path | None:
    """Configure the diagnostic log and return its folder, or ``None`` if unusable.

    Logging must never stop the app, so any problem with the log folder only
    disables the file log.
    """

    directory = log_directory()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        start_new_week_if_due(directory)
        handler = RotatingFileHandler(
            directory / LOG_FILE_NAME,
            maxBytes=LOG_MAX_BYTES,
            backupCount=1,
            encoding="utf-8",
        )
    except OSError:
        return None

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(SecretRedactingFilter(secrets))
    root = logging.getLogger()
    root.addHandler(handler)
    # Third-party libraries only report problems; the app logs in detail.
    root.setLevel(logging.WARNING)
    logger.setLevel(logging.DEBUG)
    install_exception_hooks()
    logger.info(
        "App started: version %s, %s, Python %s",
        app_version,
        platform.platform(),
        platform.python_version(),
    )
    return directory


def system_report(app_version: str, extra: dict[str, str]) -> str:
    """Return a plain-text summary of the environment for bug reports."""

    lines = [
        f"Created: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"App version: {app_version}",
        f"Platform: {platform.platform()}",
        f"Machine: {platform.machine()}",
        f"Python: {sys.version}",
        f"Frozen build: {getattr(sys, 'frozen', False)}",
        f"Log folder: {log_directory()}",
    ]
    lines += [f"{key}: {value}" for key, value in extra.items()]
    return "\n".join(lines) + "\n"


def export_diagnostics(target: Path, app_version: str, extra: dict[str, str]) -> Path:
    """Write a zip with the logs and a system report to ``target``."""

    if target.suffix.lower() != ".zip":
        target = target.with_suffix(".zip")
    for handler in logging.getLogger().handlers:
        handler.flush()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("system.txt", system_report(app_version, extra))
        for path in log_files(log_directory()):
            archive.write(path, path.name)
    logger.info("Diagnostics exported to %s", target)
    return target
