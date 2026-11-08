import pytest

from democreator.flowspec import FlowSpecError, parse_flow_spec


def test_path_flow_id_is_refused():
    """An absolute id would replace the recordings directory when the movie is named."""
    doc = {
        "flows": [
            {
                "id": "/tmp/pwned",
                "steps": [{"action": "goto", "url": "/"}],
            }
        ]
    }
    with pytest.raises(FlowSpecError, match="path"):
        parse_flow_spec(doc)
