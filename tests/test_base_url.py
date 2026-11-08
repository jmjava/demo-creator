import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_numeric_base_url_is_refused():
    """A numeric base_url used to load and then crash when a relative URL was joined."""
    doc = {
        "base_url": 3000,
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "goto", "url": "/"}],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="base_url"):
        parse_flow_spec(doc)
