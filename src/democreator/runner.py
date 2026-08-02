"""Replay curated flows against the real app at human pace, recording video.

Recording strategy: Playwright's *context-level* video capture
(``record_video_dir``) writes one continuous webm for the lifetime of the
browser context. That is what makes long-running demos possible — a single
session may span many flows and minutes of footage, unlike the per-test clips
produced by ``playwright test``. Pacing (smooth mouse travel, per-character
typing, dwell after each action) plus the injected overlay cursor/captions
make the footage read like a real human run.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from democreator.flowspec import Flow, FlowSpec, Step
from democreator.overlay import OVERLAY_JS


class DemoRunError(RuntimeError):
    """Raised when a flow step cannot be executed against the live app."""


@dataclass
class RecordedSegment:
    flow_id: str
    title: str
    video: Path


@dataclass
class DemoRecorder:
    spec: FlowSpec
    out_dir: Path
    headless: bool = True
    default_timeout_ms: int = 10_000
    _mouse_pos: tuple[float, float] = field(default=(0.0, 0.0), init=False)

    # -- public API ---------------------------------------------------------

    def record(self, flow_ids: list[str] | None = None, single_video: bool = False
               ) -> list[RecordedSegment]:
        """Record flows to webm. ``single_video`` runs every flow in one
        browser context, producing one continuous long-running movie;
        otherwise each flow becomes its own segment for later composition."""
        flows = (
            [self.spec.flow(fid) for fid in flow_ids]
            if flow_ids
            else sorted(self.spec.flows, key=lambda f: -f.priority)
        )
        if not flows:
            raise DemoRunError("no flows to record")
        self.out_dir.mkdir(parents=True, exist_ok=True)

        if single_video:
            video = self._record_session(flows, "full-demo")
            return [RecordedSegment("full-demo", "Full demo", video)]
        return [
            RecordedSegment(f.id, f.title, self._record_session([f], f.id)) for f in flows
        ]

    # -- session ------------------------------------------------------------

    def _record_session(self, flows: list[Flow], name: str) -> Path:
        from playwright.sync_api import sync_playwright

        raw_dir = self.out_dir / ".raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport=self.spec.viewport,
                record_video_dir=str(raw_dir),
                record_video_size=self.spec.viewport,
            )
            context.add_init_script(OVERLAY_JS)
            context.set_default_timeout(self.default_timeout_ms)
            page = context.new_page()
            video = page.video
            try:
                for flow in flows:
                    self._run_flow(page, flow)
                    self._sleep(page, self.spec.pacing["action_pause_ms"] * 1.5)
            finally:
                context.close()
                browser.close()
            if video is None:  # pragma: no cover - recording dir is always set
                raise DemoRunError("Playwright produced no video for this session")
            # Must resolve while the Playwright loop is still alive.
            raw_path = Path(video.path())
        final = self.out_dir / f"{name}.webm"
        shutil.move(raw_path, final)
        shutil.rmtree(raw_dir, ignore_errors=True)
        return final

    def _run_flow(self, page: Any, flow: Flow) -> None:
        self._caption(page, flow.title)
        self._sleep(page, self.spec.pacing["caption_lead_ms"])
        for i, step in enumerate(flow.steps):
            where = f"flow '{flow.id}' step {i + 1} ({step.action})"
            try:
                self._run_step(page, flow, step)
            except DemoRunError:
                raise
            except Exception as exc:
                raise DemoRunError(f"{where}: {exc}") from exc

    # -- steps --------------------------------------------------------------

    def _run_step(self, page: Any, flow: Flow, step: Step) -> None:
        pacing = self.spec.pacing
        if step.caption:
            self._caption(page, step.caption)
            self._sleep(page, pacing["caption_lead_ms"])

        if step.action == "goto":
            page.goto(self._resolve_url(flow, step.url or "/"), wait_until="load")
        elif step.action == "caption":
            self._caption(page, step.text or "")
        elif step.action == "pause":
            self._sleep(page, float(step.seconds or 0) * 1000)
        elif step.action == "expect_visible":
            locator = self._locator(page, step.locator)
            locator.first.wait_for(state="visible", timeout=step.timeout_ms or None)
        else:
            locator = self._locator(page, step.locator).first
            locator.scroll_into_view_if_needed()
            self._glide_to(page, locator)
            if step.action == "hover":
                locator.hover()
            elif step.action == "click":
                self._pulse(page)
                locator.click()
            elif step.action == "check":
                self._pulse(page)
                locator.check()
            elif step.action == "fill":
                self._pulse(page)
                locator.click()
                locator.fill("")
                locator.press_sequentially(
                    step.value or "", delay=pacing["typing_delay_ms"]
                )
            elif step.action == "select":
                self._pulse(page)
                locator.select_option(step.value)
            elif step.action == "press":
                if step.locator is not None:
                    locator.press(step.key)
                else:
                    page.keyboard.press(step.key)
            elif step.action == "scroll_to":
                pass  # scroll_into_view above is the whole action

        if step.action not in ("pause", "caption"):
            self._sleep(page, pacing["action_pause_ms"])

    # -- helpers ------------------------------------------------------------

    def _resolve_url(self, flow: Flow, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        base = flow.base_url or self.spec.base_url
        if not base:
            raise DemoRunError(
                f"relative url '{url}' needs a base_url (flow '{flow.id}' or top-level)"
            )
        return base.rstrip("/") + "/" + url.lstrip("/")

    def _locator(self, page: Any, locator: str | dict[str, Any] | None) -> Any:
        if locator is None:
            raise DemoRunError("step is missing a locator")
        if isinstance(locator, str):
            return page.locator(locator)
        kwargs = {}
        if "name" in locator:
            kwargs["name"] = locator["name"]
        if "exact" in locator:
            kwargs["exact"] = locator["exact"]
        if "role" in locator:
            return page.get_by_role(locator["role"], **kwargs)
        if "text" in locator:
            return page.get_by_text(locator["text"], exact=locator.get("exact", False))
        if "label" in locator:
            return page.get_by_label(locator["label"], exact=locator.get("exact", False))
        if "placeholder" in locator:
            return page.get_by_placeholder(locator["placeholder"], exact=locator.get("exact", False))
        if "testid" in locator:
            return page.get_by_test_id(locator["testid"])
        if "css" in locator:
            return page.locator(locator["css"])
        raise DemoRunError(f"unsupported structured locator: {locator}")

    def _glide_to(self, page: Any, locator: Any) -> None:
        """Move the real mouse (and thus the overlay cursor) smoothly to the target."""
        box = locator.bounding_box()
        if not box:
            return
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        page.mouse.move(x, y, steps=int(self.spec.pacing["mouse_steps"]))
        self._mouse_pos = (x, y)

    def _pulse(self, page: Any) -> None:
        x, y = self._mouse_pos
        self._safe_eval(page, "([x, y]) => window.__demoPulse && window.__demoPulse(x, y)", [x, y])

    def _caption(self, page: Any, text: str) -> None:
        self._safe_eval(
            page, "(t) => window.__demoShowCaption && window.__demoShowCaption(t)", text
        )

    def _sleep(self, page: Any, ms: float) -> None:
        if ms > 0:
            page.wait_for_timeout(ms)

    @staticmethod
    def _safe_eval(page: Any, script: str, arg: Any) -> None:
        try:
            page.evaluate(script, arg)
        except Exception:
            # Overlay is cosmetic; a navigation racing the evaluate must not
            # kill the recording.
            pass
