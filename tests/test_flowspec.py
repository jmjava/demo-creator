import pytest

from democreator.flowspec import (
    DEFAULT_PACING,
    FlowSpecError,
    load_flow_spec,
    parse_flow_spec,
)


def minimal_doc(**overrides):
    doc = {
        "flows": [
            {
                "id": "signup",
                "title": "Sign up",
                "steps": [
                    {"action": "goto", "url": "/"},
                    {"action": "fill", "locator": "#email", "value": "a@b.c"},
                    {"action": "click", "locator": {"role": "button", "name": "Go"}},
                ],
            }
        ],
    }
    doc.update(overrides)
    return doc


def test_parse_minimal_spec():
    spec = parse_flow_spec(minimal_doc(base_url="http://localhost:3000"))
    assert spec.base_url == "http://localhost:3000"
    assert spec.viewport == {"width": 1280, "height": 720}
    assert spec.pacing == DEFAULT_PACING
    flow = spec.flow("signup")
    assert flow.title == "Sign up"
    assert [s.action for s in flow.steps] == ["goto", "fill", "click"]
    assert flow.steps[2].locator == {"role": "button", "name": "Go"}


def test_pacing_and_viewport_overrides_merge_with_defaults():
    spec = parse_flow_spec(
        minimal_doc(pacing={"typing_delay_ms": 10}, viewport={"width": 1920, "height": 1080})
    )
    assert spec.pacing["typing_delay_ms"] == 10
    assert spec.pacing["action_pause_ms"] == DEFAULT_PACING["action_pause_ms"]
    assert spec.viewport == {"width": 1920, "height": 1080}


def test_unknown_flow_lookup_lists_known_ids():
    spec = parse_flow_spec(minimal_doc())
    with pytest.raises(FlowSpecError, match="signup"):
        spec.flow("nope")


@pytest.mark.parametrize(
    "step, message",
    [
        ({"action": "teleport"}, "unknown action"),
        ({"action": "goto"}, "requires field 'url'"),
        ({"action": "fill", "locator": "#x"}, "requires field 'value'"),
        ({"action": "click", "locator": ""}, "requires field 'locator'"),
        ({"action": "click", "locator": {"role": "button", "text": "x"}}, "exactly one"),
        ({"action": "click", "locator": {"bogus": "x"}}, "exactly one"),
        ({"action": "click", "locator": 5}, "string or mapping"),
    ],
)
def test_bad_steps_rejected(step, message):
    doc = minimal_doc()
    doc["flows"][0]["steps"] = [step]
    with pytest.raises(FlowSpecError, match=message):
        parse_flow_spec(doc)


def test_duplicate_flow_ids_rejected():
    doc = minimal_doc()
    doc["flows"].append(dict(doc["flows"][0]))
    with pytest.raises(FlowSpecError, match="duplicate flow ids"):
        parse_flow_spec(doc)


def test_empty_flows_rejected():
    with pytest.raises(FlowSpecError, match="non-empty 'flows'"):
        parse_flow_spec({"flows": []})


def test_load_flow_spec_missing_file(tmp_path):
    with pytest.raises(FlowSpecError, match="not found"):
        load_flow_spec(tmp_path / "missing.yaml")


def test_load_flow_spec_roundtrip(tmp_path):
    path = tmp_path / "flows.yaml"
    path.write_text(
        "base_url: http://x\n"
        "flows:\n"
        "  - id: f\n"
        "    steps:\n"
        "      - {action: goto, url: /}\n"
        "      - {action: pause, seconds: 2}\n",
        encoding="utf-8",
    )
    spec = load_flow_spec(path)
    assert spec.flow("f").steps[1].seconds == 2.0
