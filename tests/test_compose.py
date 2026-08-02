from pathlib import Path

import pytest

from democreator.compose import (
    ComposeError,
    build_title_card_cmd,
    build_transcode_cmd,
    compose_demo,
    plan_compose,
)


def test_plan_with_title_cards_orders_card_then_segment(tmp_path):
    segments = [("Flow A", tmp_path / "a.webm"), ("Flow B", tmp_path / "b.webm")]
    plan = plan_compose(segments, tmp_path / "out" / "demo.mp4")
    # 2 cards + 2 transcodes + concat-list write + concat
    assert len(plan.commands) == 6
    concat_write = plan.commands[-2]
    assert concat_write[0] == "__write_concat__"
    order = [Path(p).name for p in concat_write[2:]]
    assert order == ["00-card.mp4", "00-segment.mp4", "01-card.mp4", "01-segment.mp4"]
    assert plan.commands[-1][:4] == ["ffmpeg", "-y", "-f", "concat"]


def test_plan_without_title_cards(tmp_path):
    plan = plan_compose([("A", tmp_path / "a.webm")], tmp_path / "demo.mp4", title_cards=False)
    assert len(plan.commands) == 3
    assert not any("lavfi" in cmd for cmd in plan.commands)


def test_empty_segments_rejected(tmp_path):
    with pytest.raises(ComposeError, match="no recorded segments"):
        plan_compose([], tmp_path / "demo.mp4")


def test_title_card_cmd_escapes_drawtext_specials(tmp_path):
    cmd = build_title_card_cmd("Sign up: 100% 'fun'", tmp_path / "c.mp4")
    drawtext = cmd[cmd.index("-vf") + 1]
    assert "\\:" in drawtext and "\\%" in drawtext and "\\'" in drawtext


def test_transcode_normalises_to_h264_yuv420p(tmp_path):
    cmd = build_transcode_cmd(tmp_path / "a.webm", tmp_path / "a.mp4")
    assert "libx264" in cmd and "yuv420p" in cmd


def test_compose_demo_runs_commands_and_writes_concat_list(tmp_path, monkeypatch):
    ran = []

    class FakeProc:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(
        "democreator.compose.subprocess.run",
        lambda cmd, **kw: ran.append(cmd) or FakeProc(),
    )
    plan = plan_compose([("A", tmp_path / "a.webm")], tmp_path / "demo.mp4")
    out = compose_demo(plan)
    assert out == tmp_path / "demo.mp4"
    assert len(ran) == 3  # card, transcode, concat
    list_file = plan.workdir / "concat.txt"
    assert list_file.exists()
    assert list_file.read_text().count("file '") == 2


def test_compose_demo_surfaces_ffmpeg_failure(tmp_path, monkeypatch):
    class FailProc:
        returncode = 1
        stderr = "boom"

    monkeypatch.setattr("democreator.compose.subprocess.run", lambda cmd, **kw: FailProc())
    plan = plan_compose([("A", tmp_path / "a.webm")], tmp_path / "demo.mp4", title_cards=False)
    with pytest.raises(ComposeError, match="boom"):
        compose_demo(plan)
