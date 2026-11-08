from democreator.discover import discover_flows


def test_press_without_a_key_is_not_drafted(tmp_path):
    """locator.press() with no key used to draft a press of Enter."""
    spec = tmp_path / "keys.spec.ts"
    spec.write_text(
        "test('hit the control', async ({ page }) => {\n"
        "  await page.locator('#go').press();\n"
        "});\n",
        encoding="utf-8",
    )
    assert discover_flows(tmp_path) == []
