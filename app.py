"""Gradio demo UI for the Bug Hunter Agent, mounted on FastAPI."""

from __future__ import annotations

import gradio as gr

from bug_hunter_agent.agent import BugHunterAgent
from bug_hunter_agent.config import CONFIG
from bug_hunter_agent.security import RateLimitError, ValidationError, sanitize_text
from bug_hunter_agent.web import LIMITER, caller_id, make_app, run

_agent: BugHunterAgent | None = None


def _get_agent() -> BugHunterAgent:
    global _agent
    if _agent is None:
        _agent = BugHunterAgent()
    return _agent


def handle(trace: str, context: str, request: gr.Request):
    try:
        clean = sanitize_text(trace, field="an error or stack trace", min_chars=8)
    except ValidationError as exc:
        yield f"⚠️ {exc}"
        return
    ctx = ""
    if context and context.strip():
        try:
            ctx = sanitize_text(context, field="context")
        except ValidationError as exc:
            yield f"⚠️ {exc}"
            return
    try:
        LIMITER.check(caller_id(request))
    except RateLimitError as exc:
        yield f"⏳ {exc}"
        return
    if not CONFIG.api_key_present:
        yield "⚠️ The demo is not configured (missing API key). See the GitHub repo to run it locally."
        return
    yield "🔎 Analyzing the trace…"
    try:
        yield _get_agent().investigate(clean, ctx)
    except Exception:  # noqa: BLE001
        yield "⚠️ Something went wrong. Please try again in a moment."


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Bug Hunter Agent — Day 04", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "## 🐛 Bug Hunter Agent\n"
            "Paste an error or stack trace; get the **likely root causes** and fixes.\n\n"
            "*Day 04 of 14 AI Agents in 14 Days — reasoning + hypothesis generation.*"
        )
        trace = gr.Textbox(label="Error / stack trace", lines=8, placeholder="Paste the error or stack trace here…")
        context = gr.Textbox(label="Context (optional)", lines=2, placeholder="What you were doing, stack/versions, recent changes…")
        run_btn = gr.Button("Investigate", variant="primary")
        out = gr.Markdown()
        run_btn.click(handle, inputs=[trace, context], outputs=out)
    demo.queue(default_concurrency_limit=2, max_size=20)
    return demo


app = make_app(build_demo(), title="Bug Hunter Agent")

if __name__ == "__main__":
    run(app)
