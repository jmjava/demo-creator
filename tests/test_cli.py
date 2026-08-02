from pathlib import Path

import yaml
from click.testing import CliRunner

from democreator.cli import main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "taskboard"


def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "democreator" in result.output


def test_init_scaffolds_valid_flows_file(tmp_path):
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    from democreator.flowspec import load_flow_spec

    spec = load_flow_spec(tmp_path / "flows.yaml")
    assert spec.flows[0].id == "example"


def test_init_refuses_overwrite(tmp_path):
    (tmp_path / "flows.yaml").write_text("flows: []\n")
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_discover_writes_draft(tmp_path):
    out = tmp_path / "flows.yaml"
    result = CliRunner().invoke(
        main,
        ["discover", str(EXAMPLES / "tests"), "--out", str(out),
         "--base-url", "http://localhost:8123"],
    )
    assert result.exit_code == 0, result.output
    doc = yaml.safe_load(out.read_text())
    assert len(doc["flows"]) == 2
    assert "CURATE" in out.read_text()


def test_discover_refuses_overwrite_without_force(tmp_path):
    out = tmp_path / "flows.yaml"
    out.write_text("flows: []\n")
    result = CliRunner().invoke(main, ["discover", str(EXAMPLES / "tests"), "--out", str(out)])
    assert result.exit_code != 0
    assert "--force" in result.output


def test_record_rejects_bad_flows_file(tmp_path):
    bad = tmp_path / "flows.yaml"
    bad.write_text("flows:\n  - id: f\n    steps: []\n")
    result = CliRunner().invoke(main, ["record", "--flows-file", str(bad)])
    assert result.exit_code != 0
    assert "steps" in result.output


def test_compose_with_no_recordings_fails_cleanly(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    result = CliRunner().invoke(
        main,
        ["compose", "--flows-file", str(EXAMPLES / "flows.yaml"),
         "--recordings-dir", str(rec), "--out", str(tmp_path / "demo.mp4")],
    )
    assert result.exit_code != 0
    assert "no recorded segments" in result.output
