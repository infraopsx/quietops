"""Offline, self-contained human-readable reports."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json

from .ai import Brief, Note
from .cluster import Digest


def make_markdown(digest: Digest, brief: Brief | None) -> str:
    ratio = (1 - len(digest.events) / digest.examined_lines) * 100 if digest.examined_lines else 0
    lines = [
        "# QuietOps incident handoff",
        "",
        "> **Read-only analysis.** AI suggestions are hypotheses, not verified diagnoses. "
        "No server configuration was changed. All model input is redacted best-effort; review your logs before processing.",
        "",
        f"- Analyzed lines: **{digest.examined_lines}** / {digest.total_lines}",
        f"- Symptom lines: **{digest.symptom_lines}**",
        f"- Unique signatures found: **{digest.unique_events}**",
        f"- Top signatures shown to operator: **{len(digest.events)}**",
        f"- Reduction in lines needing initial review: **{ratio:.1f}%** (signature summary vs. raw lines; not a measured human time saving)",
        f"- Lines with redaction or ANSI removal: **{digest.redacted_line_count}**",
        "",
    ]
    if brief:
        lines.extend([f"## Local AI briefing ({brief.model_name})", "", brief.overview, ""])
        for title, items in [("Hypotheses (verify before acting)", brief.hypotheses), ("Read-only follow-up checks", brief.next_checks)]:
            lines.extend([f"### {title}", ""])
            lines.extend(f"- {n.text} — **{', '.join(n.event_ids)}**" for n in items)
            if not items:
                lines.append("- No evidence-linked items returned.")
            lines.append("")
        lines.extend(["### Missing information", ""])
        lines.extend(f"- {v}" for v in brief.unknowns)
        if not brief.unknowns:
            lines.append("- Not specified by model.")
        lines.append("")
    else:
        lines.extend(["## AI briefing", "", "**Not run.** This is a deterministic preview; no model-generated diagnosis is shown.", ""])
    lines.extend(["## Grouped log evidence (redacted)", ""])
    for event in digest.events:
        lines.extend([
            f"### {event.id} · {event.severity.upper()} · {event.count} occurrences",
            "",
            "```text",
            *event.samples,
            "```",
            "",
        ])
    if digest.unique_events > len(digest.events):
        lines.append(f"*{digest.unique_events - len(digest.events)} lower-ranked signature(s) not shown; increase --max-events.*")
    return "\n".join(lines).rstrip() + "\n"


def make_json(digest: Digest, brief: Brief | None) -> str:
    obj = {
        "schema_version": 1,
        "mode": "local-ai" if brief else "deterministic-preview",
        "counts": {
            "total_lines": digest.total_lines,
            "examined_lines": digest.examined_lines,
            "symptom_lines": digest.symptom_lines,
            "unique_signatures": digest.unique_events,
            "redacted_lines": digest.redacted_line_count,
        },
        "events": [
            {"id": e.id, "severity": e.severity, "count": e.count, "first_line": e.first_line, "samples": e.samples}
            for e in digest.events
        ],
        "ai": None if not brief else {
            "model": brief.model_name,
            "overview": brief.overview,
            "hypotheses": [dict(text=n.text, event_ids=n.event_ids) for n in brief.hypotheses],
            "next_checks": [dict(text=n.text, event_ids=n.event_ids) for n in brief.next_checks],
            "unknowns": brief.unknowns,
        },
    }
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _notes_html(notes: tuple[Note, ...]) -> str:
    if not notes:
        return '<div class="empty">No evidence-linked items were returned.</div>'
    return "".join(
        '<div class="note"><p>' + escape(n.text) + '</p><span class="ids">' + escape(" · ".join(n.event_ids)) + "</span></div>"
        for n in notes
    )


def make_html(digest: Digest, brief: Brief | None) -> str:
    reduction = (1 - len(digest.events) / digest.examined_lines) * 100 if digest.examined_lines else 0
    mode = "Local Gemma briefing" if brief else "Deterministic preview — model not run"
    intro = escape(brief.overview) if brief else "Open-weight AI was not run. This is a reproducible log grouping preview, not a diagnosis."
    cards = "".join(
        '<article class="event" id="' + e.id + '"><div class="event-head"><b>' + e.id + "</b>"
        + '<span class="sev ' + e.severity + '">' + escape(e.severity) + "</span>"
        + '<span class="count">' + str(e.count) + ' mentions</span></div>'
        + '<pre>' + escape(e.samples[0]) + "</pre></article>"
        for e in digest.events
    )
    ai_panel = (
        '<section class="card"><div class="section-heading"><h2>Local AI handoff</h2><span class="tiny">'
        + escape(brief.model_name) + '</span></div>'
        + '<h3>Observed log summary (deterministic, not AI-generated)</h3><p class="lead">' + intro + '</p>'
        + '<p class="tiny">The model generates the possible explanations and next checks below. Those suggestions remain unverified. Cited IDs are checked for existence and conservative topical relevance, not semantic correctness: inspect the underlying excerpts.</p>'
        + '<div class="columns"><div><h3>Possible explanations</h3>' + _notes_html(brief.hypotheses) + '</div>'
        + '<div><h3>Safe next checks</h3>' + _notes_html(brief.next_checks) + '</div></div>'
        + '<h3>What the logs cannot tell us</h3><ul>'
        + "".join('<li>' + escape(x) + '</li>' for x in brief.unknowns) + '</ul></section>'
    ) if brief else '<section class="card"><h2>Model not run</h2><p>' + intro + '</p><p>Run <code>quietops scan</code> with local Ollama to generate an evidence-linked briefing.</p></section>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuietOps — Local incident handoff</title><meta name="robots" content="noindex,nofollow">
<style>
:root{{--bg:#0b111b;--panel:#152133;--line:#2a3b51;--text:#e9f4fa;--muted:#9fb3c5;--accent:#75e2c2;--sky:#81b8ff}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;margin:0;line-height:1.6}}
main{{max-width:1040px;margin:0 auto;padding:56px 24px 80px}}h1{{font-size:clamp(38px,6vw,72px);line-height:1.05;letter-spacing:-.05em;margin:14px 0}}
h2{{font-size:24px;letter-spacing:-.025em}}h3{{font-size:15px;color:var(--accent);margin-top:28px}}p{{color:var(--muted)}}.topline,.section-heading,.event-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
.brand{{font-weight:900;letter-spacing:.05em}}.brand span{{color:var(--accent)}}.pill{{border:1px solid #35605d;border-radius:100px;color:var(--accent);padding:5px 14px;font-size:12px}}
.subtitle{{font-size:18px;max-width:690px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:32px 0}}.metric{{border:1px solid var(--line);padding:20px;background:var(--panel);border-radius:13px}}
.metric strong{{display:block;font-size:clamp(24px,3.5vw,40px);line-height:1.2}}.metric small{{color:var(--muted);font-size:12px}}.bar{{height:8px;border-radius:100px;background:#30415a;overflow:hidden;margin:25px 0 12px}}.bar i{{display:block;background:linear-gradient(90deg,#438cad,#75e2c2);height:100%;width:{reduction:.2f}%}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:30px;margin:24px 0}}.lead{{font-size:18px;color:var(--text)}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:25px}}
.note{{padding:14px 0;border-bottom:1px solid var(--line)}}.note p{{margin:0 0 6px;color:var(--text);overflow-wrap:anywhere}}.ids,.tiny{{font-size:12px;color:var(--sky)}}.empty{{color:var(--muted);font-size:14px}}
.event{{border-top:1px solid var(--line);padding:17px 0}}.event-head b{{color:var(--sky)}}.sev{{text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:.05em;border-radius:5px;padding:2px 8px}}
.sev.error{{color:#ffb8b8;background:#612c35}}.sev.warning{{color:#ffe2a8;background:#605030}}.count{{color:var(--muted);font-size:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;border-radius:10px;background:#0b1422;padding:16px;font-size:12px;color:#d2e1ec}}
.warning{{border-left:3px solid #f1bc77;padding:12px 17px;background:#372f23;color:#f4dbbd;font-size:13px;margin-top:26px}}footer{{margin-top:46px;font-size:12px;color:var(--muted)}}code{{background:#0b1422;border-radius:4px;padding:2px 5px}}
@media(max-width:720px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.columns{{grid-template-columns:1fr}}.card{{padding:20px}}}}
</style></head><body><main><div class="topline"><div class="brand">QUIET<span>OPS</span> <small>/ incident briefing</small></div><div class="pill">{escape(mode)}</div></div>
<h1>Less scrolling.<br>More signal.</h1><p class="subtitle">One local handoff for recurring log symptoms. Sensitive values are redacted before analysis; this tool never executes a repair.</p>
<div class="metrics"><div class="metric"><strong>{digest.examined_lines}</strong><small>Log lines inspected</small></div><div class="metric"><strong>{digest.symptom_lines}</strong><small>Symptom lines</small></div><div class="metric"><strong>{digest.unique_events}</strong><small>Distinct signatures</small></div><div class="metric"><strong>{reduction:.1f}%</strong><small>Initial reading reduction*</small></div></div>
<div class="bar"><i></i></div><p class="tiny">*Measured as 1 − top signatures / inspected lines, not actual human time saved.</p>
{ai_panel}
<section class="card"><div class="section-heading"><h2>Evidence fingerprints</h2><span class="tiny">Redacted before output</span></div><p>Repeated symptoms are grouped; two samples per fingerprint are retained by the scanner. Do not treat a frequency count as proof of causation.</p>{cards if cards else '<p>No error/warning signatures found in the input.</p>'}</section>
<div class="warning">Human approval required. AI explanations are hypotheses. Do not run changes on production systems without independently verifying state and having a rollback plan. Secret removal is best effort.</div>
<footer>QuietOps · open-source, local-first, read-only · Generated {escape(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))} · No analytics or third-party scripts.</footer></main></body></html>'''
