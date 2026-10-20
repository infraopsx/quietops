"""Command-line front end for QuietOps."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .ai import ModelError, query_local_model
from .cluster import analyze
from .report import make_html, make_json, make_markdown

MAX_INPUT_BYTES = 2_000_000


def _input_text(path: str) -> str:
    if path == "-":
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with open(path, "rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError(f"Input exceeds {MAX_INPUT_BYTES:,} bytes; provide a shorter window")
    return payload.decode("utf-8", errors="replace")


def _write(folder: Path, digest, brief, *, replace: bool) -> None:
    outputs = {
        "handoff.md": make_markdown(digest, brief),
        "handoff.json": make_json(digest, brief),
        "handoff.html": make_html(digest, brief),
    }
    folder.mkdir(parents=True, exist_ok=True)
    for name in outputs:
        if (folder / name).exists() and not replace:
            raise FileExistsError(f"Output {folder / name} exists. Pass --replace to overwrite")
    for name, content in outputs.items():
        (folder / name).write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="quietops",
        description="Read-only, redacted Docker/Linux incident handoff using local Gemma via Ollama.",
    )
    parser.add_argument("mode", choices=("scan", "preview"), help="scan uses local AI; preview groups logs without AI")
    parser.add_argument("input", help="UTF-8 log path, or - for stdin")
    parser.add_argument("--output-dir", default="out", metavar="DIR")
    parser.add_argument("--model", default="gemma3:1b", help="locally installed Ollama model (default: gemma3:1b)")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="loopback Ollama service only")
    parser.add_argument("--max-lines", type=int, default=8000)
    parser.add_argument("--max-events", type=int, default=12)
    parser.add_argument("--replace", action="store_true", help="overwrite prior reports")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        raw = _input_text(args.input)
        if not raw.strip():
            raise ValueError("Empty input")
        digest = analyze(raw, max_lines=args.max_lines, max_events=args.max_events)
        if not digest.events:
            print("No error/warning signatures found; empty summary may not warrant AI analysis.", file=sys.stderr)
        brief = query_local_model(digest, model=args.model, url=args.ollama_url) if args.mode == "scan" else None
        target = Path(args.output_dir)
        _write(target, digest, brief, replace=args.replace)
        print(f"QuietOps: {digest.examined_lines} lines -> {digest.unique_events} symptom signatures ({len(digest.events)} shown)")
        print(f"Mode: {'local AI ' + args.model if brief else 'deterministic preview; AI NOT run'}")
        print(f"Reports: {target / 'handoff.html'}, {target / 'handoff.md'}, {target / 'handoff.json'}")
        return 0
    except (OSError, ValueError, ModelError) as exc:
        print(f"QuietOps error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
