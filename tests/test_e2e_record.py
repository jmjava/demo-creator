"""End-to-end smoke: serve the example app, record a real paced run, compose.

Needs Playwright's chromium and ffmpeg; skipped automatically when missing.
"""

import shutil
import socket
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "examples" / "taskboard" / "app"


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


pytestmark = pytest.mark.integration

requires_stack = pytest.mark.skipif(
    not _chromium_available() or shutil.which("ffmpeg") is None,
    reason="needs Playwright chromium and ffmpeg",
)


@pytest.fixture
def app_server():
    handler = partial(SimpleHTTPRequestHandler, directory=str(APP_DIR))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{port}"
        httpd.shutdown()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@requires_stack
def test_record_flow_and_compose(tmp_path, app_server):
    from democreator.compose import compose_demo, plan_compose
    from democreator.flowspec import load_flow_spec
    from democreator.runner import DemoRecorder

    spec = load_flow_spec(REPO / "examples" / "taskboard" / "flows.yaml")
    spec.base_url = app_server
    # keep CI fast: tighten pacing but preserve the paced code paths
    spec.pacing.update(action_pause_ms=150, typing_delay_ms=15, caption_lead_ms=100)

    recorder = DemoRecorder(spec=spec, out_dir=tmp_path / "recordings")
    segments = recorder.record(["add-and-complete"])
    assert len(segments) == 1
    webm = segments[0].video
    assert webm.exists() and webm.stat().st_size > 10_000

    plan = plan_compose(
        [(segments[0].title, webm)], tmp_path / "demo.mp4",
        title_seconds=1.0,
        width=spec.viewport["width"], height=spec.viewport["height"],
    )
    out = compose_demo(plan)
    assert out.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())
    assert duration > 3.0, f"demo movie suspiciously short: {duration}s"


@requires_stack
def test_single_video_session_spans_multiple_flows(tmp_path, app_server):
    from democreator.flowspec import load_flow_spec
    from democreator.runner import DemoRecorder

    spec = load_flow_spec(REPO / "examples" / "taskboard" / "flows.yaml")
    spec.base_url = app_server
    spec.pacing.update(action_pause_ms=120, typing_delay_ms=10, caption_lead_ms=80)

    recorder = DemoRecorder(spec=spec, out_dir=tmp_path / "recordings")
    segments = recorder.record(single_video=True)
    assert len(segments) == 1
    assert segments[0].flow_id == "full-demo"
    assert segments[0].video.exists()
    assert segments[0].video.stat().st_size > 20_000


@requires_stack
def test_run_error_names_flow_and_step(tmp_path, app_server):
    from democreator.flowspec import parse_flow_spec
    from democreator.runner import DemoRecorder, DemoRunError

    spec = parse_flow_spec(
        {
            "base_url": app_server,
            "flows": [
                {
                    "id": "broken",
                    "steps": [
                        {"action": "goto", "url": "/"},
                        {"action": "click", "locator": "#does-not-exist"},
                    ],
                }
            ],
        }
    )
    recorder = DemoRecorder(spec=spec, out_dir=tmp_path, default_timeout_ms=1500)
    with pytest.raises(DemoRunError, match="flow 'broken' step 2"):
        recorder.record(["broken"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
