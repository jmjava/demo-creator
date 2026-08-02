"""Optionally start the app under demo and wait until it answers HTTP."""

from __future__ import annotations

import shlex
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Iterator


class AppLaunchError(RuntimeError):
    pass


def wait_for_http(url: str, timeout_sec: float = 30.0, interval_sec: float = 0.5) -> None:
    deadline = time.monotonic() + timeout_sec
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status < 500:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
            last_err = exc
        except Exception as exc:  # connection refused while booting
            last_err = exc
        time.sleep(interval_sec)
    raise AppLaunchError(f"app never became ready at {url} within {timeout_sec}s: {last_err}")


@contextmanager
def launched_app(
    start_command: str | None, ready_url: str | None, timeout_sec: float = 30.0
) -> Iterator[None]:
    """Run ``start_command`` (if given) for the duration of the block, waiting
    on ``ready_url`` before yielding. Without a command, just (optionally)
    wait for an already-running app."""
    proc: subprocess.Popen | None = None
    if start_command:
        proc = subprocess.Popen(shlex.split(start_command))
    try:
        if ready_url:
            try:
                wait_for_http(ready_url, timeout_sec)
            except AppLaunchError:
                if proc is not None and proc.poll() is not None:
                    raise AppLaunchError(
                        f"start command exited early with code {proc.returncode}: {start_command}"
                    ) from None
                raise
        yield
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
