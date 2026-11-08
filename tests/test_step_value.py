import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_list_fill_value_is_refused():
    """A list value used to load as the typed text \"['red']\"."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [{"action": "fill", "locator": "#task", "value": ["red"]}],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="value"):
        parse_flow_spec(doc)
