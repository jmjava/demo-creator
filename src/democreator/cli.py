"""democreator CLI: discover flows from tests, record paced demos, compose movies."""

from __future__ import annotations

from pathlib import Path

import click

from democreator import __version__


@click.group()
@click.version_option(version=__version__, prog_name="democreator")
def main() -> None:
    """Record long-running, human-paced demo movies of real GUI runs."""


@main.command()
@click.argument("tests_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--out", "out_path", default="flows.yaml", show_default=True,
              help="Where to write the draft flows file.")
@click.option("--base-url", default=None, help="Top-level base_url for the draft.")
@click.option("--force", is_flag=True, help="Overwrite an existing flows file.")
def discover(tests_dir: str, out_path: str, base_url: str | None, force: bool) -> None:
    """Draft a flows.yaml from an existing Playwright/pytest test suite.

    The draft is a starting point: curate it (order, captions, pruning)
    before recording.
    """
    from democreator.discover import draft_flows_yaml

    out = Path(out_path)
    if out.exists() and not force:
        raise click.ClickException(f"{out} already exists (use --force to overwrite)")
    doc = draft_flows_yaml(tests_dir, base_url=base_url)
    out.write_text(doc, encoding="utf-8")
    n_flows = doc.count("\n- id:") + doc.count("\n  - id:")
    click.echo(f"wrote {out} ({n_flows} draft flow(s)) — curate before recording")


def _load_spec(flows_file: str):
    from democreator.flowspec import FlowSpecError, load_flow_spec

    try:
        return load_flow_spec(flows_file)
    except FlowSpecError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command()
@click.option("--flows-file", default="flows.yaml", show_default=True,
              type=click.Path(exists=True, dir_okay=False))
@click.option("--flow", "flow_ids", multiple=True,
              help="Record only these flow id(s); repeatable. Default: all, by priority.")
@click.option("--out-dir", default="recordings", show_default=True)
@click.option("--single-video/--per-flow", default=False, show_default=True,
              help="One continuous movie for the whole session vs one segment per flow.")
@click.option("--headed", is_flag=True, help="Show the browser while recording.")
@click.option("--start-command", default=None,
              help="Command that starts the app; terminated after recording.")
@click.option("--ready-url", default=None,
              help="URL polled until the app answers (defaults to base_url when "
                   "--start-command is set).")
@click.option("--ready-timeout", default=30.0, show_default=True)
def record(flows_file: str, flow_ids: tuple[str, ...], out_dir: str, single_video: bool,
           headed: bool, start_command: str | None, ready_url: str | None,
           ready_timeout: float) -> None:
    """Replay curated flows against the real app and record video."""
    from democreator.applaunch import AppLaunchError, launched_app
    from democreator.runner import DemoRecorder, DemoRunError

    spec = _load_spec(flows_file)
    if start_command and not ready_url:
        ready_url = spec.base_url
    recorder = DemoRecorder(spec=spec, out_dir=Path(out_dir), headless=not headed)
    try:
        with launched_app(start_command, ready_url, ready_timeout):
            segments = recorder.record(list(flow_ids) or None, single_video=single_video)
    except (DemoRunError, AppLaunchError) as exc:
        raise click.ClickException(str(exc)) from exc
    for seg in segments:
        click.echo(f"recorded {seg.flow_id}: {seg.video}")


@main.command()
@click.option("--flows-file", default="flows.yaml", show_default=True,
              type=click.Path(exists=True, dir_okay=False))
@click.option("--recordings-dir", default="recordings", show_default=True,
              type=click.Path(exists=True, file_okay=False))
@click.option("--out", "out_path", default="recordings/full-demo.mp4", show_default=True)
@click.option("--title-cards/--no-title-cards", default=True, show_default=True)
@click.option("--title-seconds", default=2.5, show_default=True)
def compose(flows_file: str, recordings_dir: str, out_path: str,
            title_cards: bool, title_seconds: float) -> None:
    """Stitch per-flow recordings into one long demo movie (ffmpeg)."""
    from democreator.compose import ComposeError, compose_demo, plan_compose

    spec = _load_spec(flows_file)
    rec_dir = Path(recordings_dir)
    segments: list[tuple[str, Path]] = []
    for flow in sorted(spec.flows, key=lambda f: -f.priority):
        video = rec_dir / f"{flow.id}.webm"
        if video.exists():
            segments.append((flow.title, video))
        else:
            click.echo(f"skipping '{flow.id}': no recording at {video}", err=True)
    try:
        plan = plan_compose(
            segments, Path(out_path),
            title_cards=title_cards, title_seconds=title_seconds,
            width=spec.viewport["width"], height=spec.viewport["height"],
        )
        result = compose_demo(plan)
    except ComposeError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"composed {result}")


@main.command("generate-all")
@click.option("--flows-file", default="flows.yaml", show_default=True,
              type=click.Path(exists=True, dir_okay=False))
@click.option("--out-dir", default="recordings", show_default=True)
@click.option("--start-command", default=None)
@click.option("--ready-url", default=None)
@click.option("--ready-timeout", default=30.0, show_default=True)
@click.option("--title-cards/--no-title-cards", default=True, show_default=True)
@click.pass_context
def generate_all(ctx: click.Context, flows_file: str, out_dir: str,
                 start_command: str | None, ready_url: str | None,
                 ready_timeout: float, title_cards: bool) -> None:
    """Record every flow, then compose the full long-form demo movie."""
    ctx.invoke(
        record, flows_file=flows_file, flow_ids=(), out_dir=out_dir, single_video=False,
        headed=False, start_command=start_command, ready_url=ready_url,
        ready_timeout=ready_timeout,
    )
    ctx.invoke(
        compose, flows_file=flows_file, recordings_dir=out_dir,
        out_path=str(Path(out_dir) / "full-demo.mp4"),
        title_cards=title_cards, title_seconds=2.5,
    )


@main.command()
@click.argument("target_dir", default=".", type=click.Path(file_okay=False))
def init(target_dir: str) -> None:
    """Scaffold a starter flows.yaml in TARGET_DIR."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    flows = target / "flows.yaml"
    if flows.exists():
        raise click.ClickException(f"{flows} already exists")
    flows.write_text(STARTER_FLOWS, encoding="utf-8")
    click.echo(f"wrote {flows} — edit it, then run: democreator record")


STARTER_FLOWS = """\
# democreator flows — what to demo, in viewer order.
# Run `democreator discover <tests-dir>` to draft this from existing tests.
base_url: http://localhost:3000

viewport: {width: 1280, height: 720}

pacing:
  action_pause_ms: 900     # dwell after each action
  typing_delay_ms: 60      # per-character typing delay
  mouse_steps: 40          # smooth cursor travel
  caption_lead_ms: 700     # dwell after a caption appears

flows:
  - id: example
    title: "Example flow"
    priority: 10
    steps:
      - action: goto
        url: /
        caption: "Open the app"
      - action: click
        locator: {role: button, name: "Get started"}
        caption: "Start the main flow"
      - action: fill
        locator: "#email"
        value: "demo@example.com"
      - action: pause
        seconds: 2
"""


if __name__ == "__main__":
    main()
