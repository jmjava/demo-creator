import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_boolean_title_is_refused():
    """A boolean title used to load and was shown as the flow's caption."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "title": True,
                "steps": [{"action": "goto", "url": "/"}],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="title"):
        parse_flow_spec(doc)
