import pytest

from democreator.compose import ComposeError, plan_compose


def test_zero_frame_width_is_refused(tmp_path):
    """A zero width used to be planned as an ffmpeg frame s=0x720."""
    with pytest.raises(ComposeError, match="width"):
        plan_compose(
            [("Opening", tmp_path / "a.webm")],
            tmp_path / "demo.mp4",
            width=0,
            height=720,
        )
