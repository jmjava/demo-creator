import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_string_tags_are_refused():
    """A bare tags string used to load as one tag per character."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "tags": "beta",
                "steps": [{"action": "goto", "url": "/"}],
            }
        ]
    }
    with pytest.raises(FlowSpecError, match="tags"):
        parse_flow_spec(doc)
