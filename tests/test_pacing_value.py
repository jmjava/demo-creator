import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_infinite_action_pause_is_refused():
    """An infinite action pause would dwell forever after the next step."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "goto", "url": "/"}],
            }
        ],
        "pacing": {"action_pause_ms": float("inf")},
    }
    with pytest.raises(FlowSpecError, match="pacing"):
        parse_flow_spec(doc)
