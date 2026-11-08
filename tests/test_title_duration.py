import pytest

from democreator.compose import ComposeError, plan_compose


def test_negative_title_duration_is_refused(tmp_path):
    """A negative duration is written into the ffmpeg title card as d=-1."""
    with pytest.raises(ComposeError, match="duration"):
        plan_compose(
            [("Opening", tmp_path / "a.webm")],
            tmp_path / "demo.mp4",
            title_seconds=-1,
        )
