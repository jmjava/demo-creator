from pathlib import Path

from democreator.flowspec import Flow, FlowSpec
from democreator.runner import DemoRecorder


def test_uppercase_http_url_is_not_joined_to_the_base():
    """HTTP:// used to be treated as a path and joined onto the app origin."""
    spec = FlowSpec(flows=[], base_url="http://localhost:3000")
    flow = Flow(id="signup", title="Signup", steps=[])
    recorder = DemoRecorder(spec, Path("/tmp/unused-demo-resolve"))
    resolved = recorder._resolve_url(flow, "HTTP://localhost:3000/dashboard")
    assert resolved == "HTTP://localhost:3000/dashboard"
