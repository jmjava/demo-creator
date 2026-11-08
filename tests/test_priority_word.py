from democreator.discover import discover_flows


def test_unhappy_title_is_not_a_priority_flow(tmp_path):
    """'unhappy' contains 'happy', so substring ranking used to float it first."""
    spec = tmp_path / "journey.spec.ts"
    spec.write_text(
        "test('unhappy path', async ({ page }) => {\n"
        "  await page.goto('http://localhost/');\n"
        "});\n",
        encoding="utf-8",
    )
    flows = discover_flows(tmp_path)
    assert len(flows) == 1
    assert flows[0]["priority"] == 0
