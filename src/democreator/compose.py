"""Compose recorded webm segments into a polished long-form demo movie.

Pure command construction is separated from execution so it can be unit
tested without ffmpeg; ``compose_demo`` runs the plan.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class ComposeError(RuntimeError):
    pass


@dataclass
class ComposePlan:
    commands: list[list[str]]
    output: Path
    workdir: Path


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def build_title_card_cmd(
    text: str, out: Path, *, seconds: float = 2.5, width: int = 1280, height: int = 720
) -> list[str]:
    drawtext = (
        f"drawtext=text='{_escape_drawtext(text)}':fontcolor=white:fontsize={height // 14}"
        ":x=(w-text_w)/2:y=(h-text_h)/2"
    )
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x111827:s={width}x{height}:d={seconds}",
        "-vf", drawtext,
        "-r", "25", "-pix_fmt", "yuv420p", "-an",
        str(out),
    ]


def build_transcode_cmd(src: Path, out: Path) -> list[str]:
    """Normalise a segment (webm or mp4) to concat-safe h264 mp4."""
    return [
        "ffmpeg", "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-r", "25", "-pix_fmt", "yuv420p", "-an",
        str(out),
    ]


def build_concat_cmd(list_file: Path, out: Path) -> list[str]:
    return [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out),
    ]


def plan_compose(
    segments: list[tuple[str, Path]],
    output: Path,
    *,
    title_cards: bool = True,
    title_seconds: float = 2.5,
    width: int = 1280,
    height: int = 720,
) -> ComposePlan:
    """Build the ffmpeg command sequence: [title card +] transcode per segment,
    then a concat of everything into ``output``.

    ``segments`` is an ordered list of (title, video_path).
    """
    if not segments:
        raise ComposeError("nothing to compose: no recorded segments")
    workdir = output.parent / ".compose"
    commands: list[list[str]] = []
    parts: list[Path] = []
    for i, (title, video) in enumerate(segments):
        if title_cards:
            card = workdir / f"{i:02d}-card.mp4"
            commands.append(
                build_title_card_cmd(
                    title, card, seconds=title_seconds, width=width, height=height
                )
            )
            parts.append(card)
        norm = workdir / f"{i:02d}-segment.mp4"
        commands.append(build_transcode_cmd(video, norm))
        parts.append(norm)

    list_file = workdir / "concat.txt"
    commands.append(["__write_concat__", str(list_file)] + [str(p) for p in parts])
    commands.append(build_concat_cmd(list_file, output))
    return ComposePlan(commands=commands, output=output, workdir=workdir)


def compose_demo(plan: ComposePlan) -> Path:
    plan.workdir.mkdir(parents=True, exist_ok=True)
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    for cmd in plan.commands:
        if cmd[0] == "__write_concat__":
            list_file = Path(cmd[1])
            list_file.write_text(
                "".join(f"file '{p}'\n" for p in cmd[2:]), encoding="utf-8"
            )
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ComposeError(
                f"command failed ({' '.join(cmd[:6])} ...):\n{proc.stderr[-2000:]}"
            )
    return plan.output
