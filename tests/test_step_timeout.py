import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_negative_step_timeout_is_refused():
    """A timeout of -1 used to load and was handed to the step wait."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "click", "locator": "#go", "timeout_ms": -1}],
            }
        ]
    }
    with pytest.raises(FlowSpecError, match="timeout_ms"):
        parse_flow_spec(doc)
