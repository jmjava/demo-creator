"""Flow specification: the curated YAML contract between discovery and the recorder.

A flows file describes *what to demo* as an ordered list of flows, each an ordered
list of steps. Discovery drafts this file from existing tests; humans curate it;
the recorder replays it against the real running app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class FlowSpecError(ValueError):
    """Raised when a flows file is malformed."""


#: action name -> required step fields (beyond ``action`` itself)
ACTIONS: dict[str, tuple[str, ...]] = {
    "goto": ("url",),
    "click": ("locator",),
    "hover": ("locator",),
    "fill": ("locator", "value"),
    "select": ("locator", "value"),
    "press": ("key",),
    "check": ("locator",),
    "scroll_to": ("locator",),
    "expect_visible": ("locator",),
    "pause": ("seconds",),
    "caption": ("text",),
}

#: keys accepted in a structured (dict) locator
LOCATOR_KINDS = ("css", "text", "role", "label", "placeholder", "testid")


DEFAULT_PACING: dict[str, Any] = {
    # dwell after each completed action so viewers can absorb the result
    "action_pause_ms": 900,
    # per-character delay while typing into inputs
    "typing_delay_ms": 60,
    # interpolation steps for smooth mouse travel between targets
    "mouse_steps": 40,
    # dwell after a caption change before the action fires
    "caption_lead_ms": 700,
}

DEFAULT_VIEWPORT = {"width": 1280, "height": 720}


@dataclass
class Step:
    action: str
    locator: str | dict[str, Any] | None = None
    url: str | None = None
    value: str | None = None
    key: str | None = None
    seconds: float | None = None
    text: str | None = None
    caption: str | None = None
    timeout_ms: int | None = None


@dataclass
class Flow:
    id: str
    title: str
    steps: list[Step]
    description: str = ""
    base_url: str | None = None
    source: str | None = None
    priority: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class FlowSpec:
    flows: list[Flow]
    base_url: str | None = None
    viewport: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_VIEWPORT))
    pacing: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_PACING))

    def flow(self, flow_id: str) -> Flow:
        for f in self.flows:
            if f.id == flow_id:
                return f
        known = ", ".join(f.id for f in self.flows) or "<none>"
        raise FlowSpecError(f"unknown flow '{flow_id}' (known: {known})")


def _validate_locator(locator: Any, where: str) -> str | dict[str, Any]:
    if isinstance(locator, str):
        if not locator.strip():
            raise FlowSpecError(f"{where}: locator must not be empty")
        return locator
    if isinstance(locator, dict):
        kinds = [k for k in locator if k in LOCATOR_KINDS]
        if len(kinds) != 1:
            raise FlowSpecError(
                f"{where}: structured locator needs exactly one of {LOCATOR_KINDS}, got {locator}"
            )
        extras = set(locator) - set(LOCATOR_KINDS) - {"name", "exact"}
        if extras:
            raise FlowSpecError(f"{where}: unknown locator keys {sorted(extras)}")
        return locator
    raise FlowSpecError(f"{where}: locator must be a string or mapping, got {type(locator).__name__}")


def _parse_step(raw: Any, where: str) -> Step:
    if not isinstance(raw, dict):
        raise FlowSpecError(f"{where}: step must be a mapping, got {type(raw).__name__}")
    action = raw.get("action")
    if action not in ACTIONS:
        raise FlowSpecError(
            f"{where}: unknown action {action!r} (expected one of {sorted(ACTIONS)})"
        )
    for required in ACTIONS[action]:
        if raw.get(required) in (None, ""):
            raise FlowSpecError(f"{where}: action '{action}' requires field '{required}'")
    step = Step(
        action=action,
        url=raw.get("url"),
        value=None if raw.get("value") is None else str(raw["value"]),
        key=raw.get("key"),
        seconds=None if raw.get("seconds") is None else float(raw["seconds"]),
        text=raw.get("text"),
        caption=raw.get("caption"),
        timeout_ms=None if raw.get("timeout_ms") is None else int(raw["timeout_ms"]),
    )
    if raw.get("locator") is not None:
        step.locator = _validate_locator(raw["locator"], where)
    return step


def _parse_flow(raw: Any, index: int) -> Flow:
    where = f"flows[{index}]"
    if not isinstance(raw, dict):
        raise FlowSpecError(f"{where}: flow must be a mapping")
    flow_id = raw.get("id")
    if not flow_id or not isinstance(flow_id, str):
        raise FlowSpecError(f"{where}: flow needs a non-empty string 'id'")
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise FlowSpecError(f"{where} ('{flow_id}'): flow needs a non-empty 'steps' list")
    steps = [
        _parse_step(s, f"{where}.steps[{i}] (flow '{flow_id}')") for i, s in enumerate(raw_steps)
    ]
    return Flow(
        id=flow_id,
        title=raw.get("title") or flow_id,
        steps=steps,
        description=raw.get("description", ""),
        base_url=raw.get("base_url"),
        source=raw.get("source"),
        priority=int(raw.get("priority", 0)),
        tags=list(raw.get("tags", [])),
    )


def parse_flow_spec(data: Any) -> FlowSpec:
    if not isinstance(data, dict):
        raise FlowSpecError("flows file must be a YAML mapping at the top level")
    raw_flows = data.get("flows")
    if not isinstance(raw_flows, list) or not raw_flows:
        raise FlowSpecError("flows file needs a non-empty 'flows' list")
    flows = [_parse_flow(f, i) for i, f in enumerate(raw_flows)]
    ids = [f.id for f in flows]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise FlowSpecError(f"duplicate flow ids: {sorted(dupes)}")

    viewport = dict(DEFAULT_VIEWPORT)
    viewport.update(data.get("viewport") or {})
    pacing = dict(DEFAULT_PACING)
    pacing.update(data.get("pacing") or {})
    return FlowSpec(
        flows=flows,
        base_url=data.get("base_url"),
        viewport=viewport,
        pacing=pacing,
    )


def load_flow_spec(path: str | Path) -> FlowSpec:
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FlowSpecError(f"flows file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise FlowSpecError(f"invalid YAML in {path}: {exc}") from exc
    return parse_flow_spec(data)
