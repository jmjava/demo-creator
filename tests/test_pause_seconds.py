import pytest

from democreator.flowspec import Flow, FlowSpec, Step
from democreator.runner import DemoRecorder, DemoRunError


def test_infinite_pause_is_refused(tmp_path):
    """An infinite pause would wait forever inside the recording session."""
    flow = Flow(id="hold", title="Hold", steps=[Step(action="pause", seconds=float("inf"))])
    recorder = DemoRecorder(FlowSpec(flows=[flow]), tmp_path)

    def fail_if_slept(_ms):
        raise AssertionError("slept")

    page = type("Page", (), {"wait_for_timeout": staticmethod(fail_if_slept)})()
    with pytest.raises(DemoRunError, match="pause"):
        recorder._run_step(page, flow, flow.steps[0])
