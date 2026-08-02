# demo-creator

Record **long-running, human-paced demo movies of real GUI runs**. Sibling
project to [documentation-generator](https://github.com/jmjava/documentation-generator)
(`docgen`): where docgen *synthesises* narrated videos (Manim, TTS, ffmpeg),
`democreator` **captures the real app in motion** — the browser actually
navigating, typing, and clicking, recorded as one continuous movie.

## Why Playwright (and how it gives long demos)

Playwright is the engine, but **not** its test runner. `playwright test`'s
video option produces one short clip per test — choppy robot footage. Instead:

- **Tests are hints, not the demo.** `democreator discover` statically parses
  your existing Playwright specs (TS/JS) or pytest-playwright files and drafts
  the important user flows as a `flows.yaml`. `@smoke` / `critical` tags float
  flows to the top. You then curate that file: reorder, drop assertion noise,
  add viewer captions.
- **Long-running recording** comes from Playwright's *context-level* video
  capture (`record_video_dir`): one continuous webm for the lifetime of a
  browser context, which can span many flows and minutes of footage
  (`democreator record --single-video`). No per-test chopping.
- **Human pacing** makes it watchable: a visible software cursor glides to
  each target, clicks ripple, typing happens character by character, a caption
  bar narrates each step, and every action is followed by a dwell so viewers
  can absorb the result.
- **ffmpeg composition** turns per-flow segments into a polished movie with
  title cards (`democreator compose`), same post-processing philosophy as
  docgen.

Alternatives considered: raw ffmpeg/x11grab screen capture (needs a display
stack, fragile in CI, no DOM awareness for pacing or captions), Selenium
(no built-in video, weaker auto-waiting), and VHS (terminal-only). Playwright
records headless, knows where elements are (so the cursor can glide to them),
and already speaks the language your e2e tests are written in.

## Pipeline

```
existing e2e tests ──discover──▶ flows.yaml ──(curate)──▶ record ──▶ *.webm ──compose──▶ demo.mp4
                                                 ▲                    real app, real browser,
                                        the human-owned artifact      continuous context video
```

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install --with-deps chromium   # one-time browser download
# ffmpeg required for compose (apt install ffmpeg)
```

## Quick start (bundled example)

```bash
# 1. draft flows from the example test suite
democreator discover examples/taskboard/tests --base-url http://localhost:8123 --out /tmp/draft.yaml

# 2. record the curated flows against the real app
#    (--start-command boots the app and tears it down afterwards)
cd examples/taskboard
democreator record --start-command "python3 -m http.server 8123 --directory app" \
                   --single-video          # one continuous long-running movie
# or per-flow segments + stitched movie with title cards:
democreator generate-all --start-command "python3 -m http.server 8123 --directory app"
open recordings/full-demo.mp4
```

For your own app: `democreator init`, point `base_url` at the running app (or
pass `--start-command`), curate `flows.yaml`, then `democreator generate-all`.

## CLI

| Command | Description |
|---------|-------------|
| `democreator init [DIR]` | Scaffold a starter `flows.yaml` |
| `democreator discover TESTS_DIR [--out flows.yaml] [--base-url URL] [--force]` | Draft flows from Playwright TS/JS specs and pytest-playwright files; `@smoke`/`critical` tags set priority |
| `democreator record [--flow ID]... [--single-video] [--headed] [--start-command CMD] [--ready-url URL]` | Replay curated flows against the real app, recording continuous context video (webm) |
| `democreator compose [--no-title-cards] [--out demo.mp4]` | Stitch per-flow recordings into one movie with ffmpeg title cards |
| `democreator generate-all [--start-command CMD]` | Record every flow, then compose `recordings/full-demo.mp4` |

## flows.yaml

```yaml
base_url: http://localhost:3000
viewport: {width: 1280, height: 720}
pacing:
  action_pause_ms: 900     # dwell after each action
  typing_delay_ms: 60      # per-character typing
  mouse_steps: 40          # smooth cursor travel
  caption_lead_ms: 700     # dwell after a caption appears

flows:
  - id: add-and-complete
    title: "Add and complete a task"
    priority: 10           # higher records/composes first
    source: tests/taskboard.spec.ts   # provenance from discovery
    steps:
      - action: goto
        url: /
        caption: "Open the taskboard"          # shown in the caption bar
      - action: fill
        locator: "#new-task"                   # string = CSS/Playwright selector
        value: "Write the quarterly report"
      - action: click
        locator: {role: button, name: "Add task"}   # structured getBy* locator
      - action: expect_visible
        locator: "#tasks li"
      - action: pause
        seconds: 1.5
```

Actions: `goto`, `click`, `hover`, `fill`, `select`, `press`, `check`,
`scroll_to`, `expect_visible`, `pause`, `caption`. Structured locators support
`role` (+`name`), `text`, `label`, `placeholder`, `testid`, `css`.

## Development

```bash
pip install -e ".[dev]" && playwright install --with-deps chromium
pytest                       # unit tests need no browser
pytest -m integration        # real headless recording + ffmpeg compose
ruff check src tests
```

## Relationship to docgen

`docgen` deliberately removed its Playwright path — a UI recorder is a
consumer-project concern, not a generic narration library's. `democreator` is
that concern given its own home. Natural future bridge: feed `democreator`
recordings into a docgen bundle as real-footage segments alongside Manim
scenes, and reuse docgen's TTS narration over recorded flows.

## System dependencies

- **Playwright chromium** — `playwright install --with-deps chromium`
- **ffmpeg** — composition (title cards, transcode, concat)
