from democreator.discover import discover_flows


def test_empty_fill_is_not_drafted(tmp_path):
    """A fill of '' used to draft a flow the spec loader then refuses."""
    spec = tmp_path / "clear.spec.ts"
    spec.write_text(
        "test('clear the field', async ({ page }) => {\n"
        "  await page.fill('#x', '');\n"
        "});\n",
        encoding="utf-8",
    )
    assert discover_flows(tmp_path) == []
