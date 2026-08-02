import pytest
import yaml

from democreator.discover import discover_flows, draft_flows_yaml
from democreator.flowspec import parse_flow_spec

JS_SPEC = """
import { test, expect } from '@playwright/test';

test('add and complete a task @smoke', async ({ page }) => {
  await page.goto('http://localhost:8123/');
  await page.fill('#new-task', 'Report');
  await page.getByRole('button', { name: 'Add task' }).click();
  await expect(page.locator('#tasks li')).toBeVisible();
  await page.locator('#tasks li input').check();
});

test('no ui actions here', async () => {
  const x = 1 + 1;
});
"""

PY_SPEC = '''
def test_login_flow(page):
    page.goto("http://localhost:9000/login")
    page.get_by_label("Email").fill("demo@example.com")
    page.press("#password", "Enter")
    expect(page.get_by_text("Welcome")).to_be_visible()
'''


@pytest.fixture
def tests_dir(tmp_path):
    (tmp_path / "e2e").mkdir()
    (tmp_path / "e2e" / "taskboard.spec.ts").write_text(JS_SPEC, encoding="utf-8")
    (tmp_path / "e2e" / "test_login.py").write_text(PY_SPEC, encoding="utf-8")
    return tmp_path


def test_discover_js_flow(tests_dir):
    flows = discover_flows(tests_dir)
    js = next(f for f in flows if "task" in f["id"])
    assert js["title"] == "add and complete a task"
    assert js["tags"] == ["smoke"]
    assert js["priority"] == 10
    assert js["base_url"] == "http://localhost:8123"
    assert js["steps"] == [
        {"action": "goto", "url": "/"},
        {"action": "fill", "locator": "#new-task", "value": "Report"},
        {"action": "click", "locator": {"role": "button", "name": "Add task"}},
        {"action": "expect_visible", "locator": "#tasks li"},
        {"action": "check", "locator": "#tasks li input"},
    ]


def test_discover_python_flow(tests_dir):
    flows = discover_flows(tests_dir)
    py = next(f for f in flows if "login" in f["id"])
    assert py["title"] == "login flow"
    assert py["base_url"] == "http://localhost:9000"
    assert py["steps"] == [
        {"action": "goto", "url": "/login"},
        {"action": "fill", "locator": {"label": "Email"}, "value": "demo@example.com"},
        {"action": "press", "locator": "#password", "key": "Enter"},
        {"action": "expect_visible", "locator": {"text": "Welcome"}},
    ]


def test_smoke_tagged_flow_sorted_first(tests_dir):
    flows = discover_flows(tests_dir)
    assert flows[0]["priority"] == 10


def test_tests_without_ui_actions_skipped(tests_dir):
    flows = discover_flows(tests_dir)
    assert not any("no ui actions" in f["title"] for f in flows)


def test_node_modules_ignored(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "x.spec.ts").write_text(JS_SPEC, encoding="utf-8")
    assert discover_flows(tmp_path) == []


def test_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_flows(tmp_path / "nope")


def test_draft_yaml_is_loadable_by_flowspec(tests_dir):
    doc = draft_flows_yaml(tests_dir, base_url="http://localhost:8123")
    spec = parse_flow_spec(yaml.safe_load(doc))
    assert spec.base_url == "http://localhost:8123"
    assert len(spec.flows) == 2


def test_example_spec_in_repo_discovers_two_flows():
    from pathlib import Path

    tests = Path(__file__).resolve().parents[1] / "examples" / "taskboard" / "tests"
    flows = discover_flows(tests)
    assert len(flows) == 2
    assert flows[0]["tags"] == ["smoke"]
