"""Draft demo flows from an existing Playwright test suite.

Tests are *hints*, not the demo itself: this module statically scans Playwright
JS/TS specs and pytest-playwright files for the user-visible actions they
perform (goto / click / fill / ...) and emits a draft ``flows.yaml``. Humans
then curate that file — reorder, drop assertions-only noise, add captions —
and the recorder replays it against the real running app.

Static parsing is intentionally best-effort. Helper functions, loops, and
page-object indirection will not be followed; the draft marks each flow with
its source file so a curator can fill gaps.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

JS_SUFFIXES = (".spec.ts", ".spec.js", ".spec.mjs", ".test.ts", ".test.js")
PRIORITY_TAGS = ("smoke", "critical", "core", "happy")

# One alternative per quote style, each excluding its own delimiter so a
# lazy match can never swallow the closing quote and bleed into the next
# statement. Group names get a per-pattern suffix to stay unique.
_JS_STR = r"(?:'(?P<{name}_sq>[^'\n]*)'|\"(?P<{name}_dq>[^\"\n]*)\"|`(?P<{name}_bt>[^`\n]*)`)"
_PY_STR = r"(?:'(?P<{name}_sq>[^'\n]*)'|\"(?P<{name}_dq>[^\"\n]*)\")"


def _s(template: str, name: str) -> str:
    return template.format(name=name)


def _g(m: re.Match, name: str) -> str | None:
    """Value of a quoted-string group regardless of which quote style hit."""
    groups = m.groupdict()
    for suffix in ("_sq", "_dq", "_bt"):
        value = groups.get(name + suffix)
        if value is not None:
            return value
    return None


_METHOD_ACTIONS = {
    "click": "click",
    "dblclick": "click",
    "hover": "hover",
    "check": "check",
    "fill": "fill",
    "press": "press",
    "selectOption": "select",
    "select_option": "select",
}

_GETTER_KINDS = {
    "getByRole": "role",
    "getByText": "text",
    "getByLabel": "label",
    "getByPlaceholder": "placeholder",
    "getByTestId": "testid",
    "get_by_role": "role",
    "get_by_text": "text",
    "get_by_label": "label",
    "get_by_placeholder": "placeholder",
    "get_by_test_id": "testid",
}

_JS_METHODS = r"click|dblclick|hover|check|fill|press|selectOption"
_PY_METHODS = r"click|dblclick|hover|check|fill|press|select_option"
_JS_GETTERS = r"getByRole|getByText|getByLabel|getByPlaceholder|getByTestId"
_PY_GETTERS = r"get_by_role|get_by_text|get_by_label|get_by_placeholder|get_by_test_id"


def _patterns(string_tpl: str, methods: str, getters: str) -> list[tuple[re.Pattern, str]]:
    """Ordered (regex, kind) pairs shared by the JS and Python scanners."""
    S = lambda name: _s(string_tpl, name)  # noqa: E731
    return [
        (re.compile(rf"page\.goto\(\s*{S('url')}", re.DOTALL), "goto"),
        (
            re.compile(
                rf"page\.locator\(\s*{S('sel')}\s*\)\s*"
                rf"\.(?P<method>{methods})\(\s*(?:{S('arg')})?",
                re.DOTALL,
            ),
            "locator_chain",
        ),
        (
            re.compile(
                rf"page\.(?P<getter>{getters})\(\s*{S('val')}\s*"
                rf"(?:,\s*(?P<opts>[^)]*))?\)\s*"
                rf"\.(?P<method>{methods})\(\s*(?:{S('arg')})?",
                re.DOTALL,
            ),
            "getter_chain",
        ),
        (
            re.compile(
                rf"page\.(?P<method>{methods})\(\s*{S('sel')}\s*(?:,\s*{S('arg')})?",
                re.DOTALL,
            ),
            "direct",
        ),
        (
            re.compile(
                rf"expect\(\s*page\.locator\(\s*{S('sel')}\s*\)\s*\)\s*"
                r"\.(?:toBeVisible|toBeInViewport|to_be_visible)\(",
                re.DOTALL,
            ),
            "expect_locator",
        ),
        (
            re.compile(
                rf"expect\(\s*page\.(?P<getter>{getters})\(\s*{S('val')}\s*"
                rf"(?:,\s*(?P<opts>[^)]*))?\)\s*\)\s*"
                r"\.(?:toBeVisible|toBeInViewport|to_be_visible)\(",
                re.DOTALL,
            ),
            "expect_getter",
        ),
    ]


_JS_PATTERNS = _patterns(_JS_STR, _JS_METHODS, _JS_GETTERS)
_PY_PATTERNS = _patterns(_PY_STR, _PY_METHODS, _PY_GETTERS)

_NAME_OPT = re.compile(r"name\s*[:=]\s*(?P<q>['\"`])(?P<name>.*?)(?P=q)")


def _getter_locator(getter: str, val: str, opts: str | None) -> dict[str, Any]:
    locator: dict[str, Any] = {_GETTER_KINDS[getter]: val}
    if opts:
        m = _NAME_OPT.search(opts)
        if m:
            locator["name"] = m.group("name")
    return locator


def _action_step(method: str, locator: str | dict, arg: str | None) -> dict[str, Any] | None:
    action = _METHOD_ACTIONS.get(method)
    if action is None:
        return None
    step: dict[str, Any] = {"action": action, "locator": locator}
    if action == "fill" or action == "select":
        step["value"] = arg or ""
    elif action == "press":
        step["key"] = arg or "Enter"
    return step


def _scan_steps(body: str, patterns: list[tuple[re.Pattern, str]]) -> list[dict[str, Any]]:
    matches: list[tuple[int, int, dict[str, Any]]] = []
    for regex, kind in patterns:
        for m in regex.finditer(body):
            step: dict[str, Any] | None = None
            if kind == "goto":
                step = {"action": "goto", "url": _g(m, "url") or ""}
            elif kind in ("direct", "locator_chain"):
                step = _action_step(m.group("method"), _g(m, "sel") or "", _g(m, "arg"))
            elif kind == "getter_chain":
                locator = _getter_locator(m.group("getter"), _g(m, "val") or "", m.group("opts"))
                step = _action_step(m.group("method"), locator, _g(m, "arg"))
            elif kind == "expect_locator":
                step = {"action": "expect_visible", "locator": _g(m, "sel")}
            elif kind == "expect_getter":
                locator = _getter_locator(m.group("getter"), _g(m, "val") or "", m.group("opts"))
                step = {"action": "expect_visible", "locator": locator}
            if step is not None:
                matches.append((m.start(), m.end(), step))
    matches.sort(key=lambda t: t[0])
    # Drop overlapping matches: e.g. a locator-chain hit also matches the
    # "direct" pattern at the same offset region.
    steps: list[dict[str, Any]] = []
    last_end = -1
    for start, end, step in matches:
        if start < last_end:
            continue
        steps.append(step)
        last_end = end
    return steps


def _match_braces(text: str, open_idx: int) -> int:
    """Index just past the ``}`` matching the ``{`` at ``open_idx`` (-1 if unbalanced)."""
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c in "'\"`":
            quote = c
            i += 1
            while i < len(text) and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                i += 1
        i += 1
    return -1


_JS_TEST_HEAD = re.compile(
    r"(?:^|\W)(?:test|it)\s*\(\s*(?P<q>['\"`])(?P<title>.*?)(?P=q)\s*,", re.DOTALL
)


def _js_test_blocks(source: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for m in _JS_TEST_HEAD.finditer(source):
        # The body brace is the first "{" after "=>" (arrow fn) or after
        # "function(...)" — never the "({ page })" destructuring brace.
        arrow = source.find("=>", m.end())
        anchor = arrow + 2 if arrow != -1 else m.end()
        open_idx = source.find("{", anchor)
        if open_idx == -1:
            continue
        close = _match_braces(source, open_idx)
        if close == -1:
            continue
        blocks.append((m.group("title"), source[open_idx:close]))
    return blocks


_PY_TEST_HEAD = re.compile(r"^def (?P<name>test_\w+)\s*\(.*?\)(?:\s*->\s*[^:]+)?:", re.MULTILINE)


def _py_test_blocks(source: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    heads = list(_PY_TEST_HEAD.finditer(source))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(source)
        title = m.group("name").removeprefix("test_").replace("_", " ")
        blocks.append((title, source[m.end():end]))
    return blocks


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "flow"


def _tags(title: str) -> list[str]:
    return [t.lstrip("@").lower() for t in re.findall(r"@[\w-]+", title)]


def _priority(title: str, tags: list[str]) -> int:
    haystack = " ".join([title.lower(), *tags])
    return 10 if any(tag in haystack for tag in PRIORITY_TAGS) else 0


_ORIGIN = re.compile(r"^(https?://[^/]+)")


def _hoist_base_url(flow: dict[str, Any]) -> None:
    """If goto URLs share one origin, hoist it to the flow's base_url."""
    origins = set()
    for step in flow["steps"]:
        if step["action"] == "goto":
            m = _ORIGIN.match(step.get("url", ""))
            origins.add(m.group(1) if m else None)
    if len(origins) == 1 and (origin := origins.pop()):
        flow["base_url"] = origin
        for step in flow["steps"]:
            if step["action"] == "goto":
                step["url"] = step["url"][len(origin):] or "/"


def discover_flows(tests_dir: str | Path) -> list[dict[str, Any]]:
    """Scan a test tree and return draft flow dicts, highest priority first."""
    tests_dir = Path(tests_dir)
    if not tests_dir.is_dir():
        raise FileNotFoundError(f"tests directory not found: {tests_dir}")

    flows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    files = sorted(
        p
        for p in tests_dir.rglob("*")
        if p.is_file()
        and "node_modules" not in p.parts
        and (p.name.endswith(JS_SUFFIXES) or (p.name.startswith("test_") and p.suffix == ".py"))
    )
    for path in files:
        source = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".py":
            blocks, patterns = _py_test_blocks(source), _PY_PATTERNS
        else:
            blocks, patterns = _js_test_blocks(source), _JS_PATTERNS
        for title, body in blocks:
            steps = _scan_steps(body, patterns)
            if not steps:
                continue
            flow_id = _slug(f"{path.stem.split('.')[0]}-{title}")
            n = 2
            while flow_id in seen_ids:
                flow_id = f"{_slug(title)}-{n}"
                n += 1
            seen_ids.add(flow_id)
            tags = _tags(title)
            flow: dict[str, Any] = {
                "id": flow_id,
                "title": re.sub(r"\s*@[\w-]+", "", title).strip() or flow_id,
                "source": str(path),
                "priority": _priority(title, tags),
                "steps": steps,
            }
            if tags:
                flow["tags"] = tags
            _hoist_base_url(flow)
            flows.append(flow)

    flows.sort(key=lambda f: -f["priority"])
    return flows


def draft_flows_yaml(tests_dir: str | Path, base_url: str | None = None) -> str:
    """Render discovered flows as a curated-ready flows.yaml document."""
    flows = discover_flows(tests_dir)
    doc: dict[str, Any] = {}
    if base_url:
        doc["base_url"] = base_url
    doc["flows"] = flows
    header = (
        "# Draft demo flows discovered from tests — CURATE BEFORE RECORDING.\n"
        "# Reorder steps, drop assertion noise, add `caption:` lines for viewers,\n"
        "# and delete flows that are not demo-worthy. Each flow lists its source test.\n"
    )
    return header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
