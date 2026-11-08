import pytest

from democreator.applaunch import AppLaunchError, wait_for_http


def test_infinite_ready_timeout_is_refused(monkeypatch):
    """Infinity used to make the ready poll wait forever."""

    def explode(*_args, **_kwargs):
        raise RuntimeError("polled")

    def stop_sleep(*_args, **_kwargs):
        raise BaseException("slept")

    monkeypatch.setattr("urllib.request.urlopen", explode)
    monkeypatch.setattr("time.sleep", stop_sleep)
    with pytest.raises(AppLaunchError, match="timeout"):
        wait_for_http("http://127.0.0.1:9/", timeout_sec=float("inf"))
