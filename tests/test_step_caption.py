import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_boolean_step_caption_is_refused():
    """A boolean caption used to load and was shown on the overlay."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "goto", "url": "/", "caption": True}],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="caption"):
        parse_flow_spec(doc)
