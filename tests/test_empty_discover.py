from click.testing import CliRunner

from democreator.cli import main


def test_discover_refuses_a_suite_with_no_flows(tmp_path):
    """An empty suite used to write flows: [] and exit as a success."""
    tests = tmp_path / "tests"
    tests.mkdir()
    out = tmp_path / "flows.yaml"
    result = CliRunner().invoke(main, ["discover", str(tests), "--out", str(out)])
    assert result.exit_code != 0
    assert "no demo flows" in result.output
    assert not out.exists()
