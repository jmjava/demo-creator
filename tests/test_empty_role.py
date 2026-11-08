import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_empty_role_locator_is_refused():
    """An empty role used to load and would be searched for at record time."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "click", "locator": {"role": ""}}],
            }
        ]
    }
    with pytest.raises(FlowSpecError, match="role"):
        parse_flow_spec(doc)
