import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_string_false_exact_is_refused():
    """The string "false" used to load, and it is truthy, so the match was exact."""
    doc = {
        "flows": [
            {
                "id": "signup",
                "steps": [
                    {"action": "click", "locator": {"role": "button", "exact": "false"}},
                ],
            }
        ],
    }
    with pytest.raises(FlowSpecError, match="exact must be a boolean"):
        parse_flow_spec(doc)
