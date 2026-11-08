from democreator.discover import discover_flows


def test_empty_goto_is_not_drafted(tmp_path):
    """A goto of '' used to draft a flow the spec loader then refuses."""
    spec = tmp_path / "blank.spec.ts"
    spec.write_text(
        "test('blank', async ({ page }) => {\n"
        "  await page.goto('');\n"
        "});\n",
        encoding="utf-8",
    )
    assert discover_flows(tmp_path) == []
