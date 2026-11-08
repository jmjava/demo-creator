import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_boolean_priority_is_refused():
    """A boolean priority used to load as 1 and sort above the default."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "priority": True,
                "steps": [{"action": "goto", "url": "/"}],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="priority"):
        parse_flow_spec(doc)
