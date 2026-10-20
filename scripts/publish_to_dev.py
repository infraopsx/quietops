"""Publish the verified QuietOps DEV challenge entry using a GitHub Actions secret.

This file is never run on pull_request events; do not paste API keys into source,
issue comments, PRs, console transcripts, or chat.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://dev.to/api"
ARTICLE_TITLE = "QuietOps: Local Gemma Turns 240 Docker Log Lines Into Five Signals 🦥"
ARTICLE_FILE = Path(__file__).resolve().parents[1] / "submissions" / "dev-week3.md"
TAGS = ["devchallenge", "hf26challenge", "opensource", "python"]
REQUIRED_SECTIONS = (
    "## What I Built",
    "## Demo",
    "## Code",
    "## How I Built It",
    "## Why Does Open Innovation Matter?",
    "## The Lazy Payoff",
    "## Prize Categories",
)


def article_body() -> str:
    body = ARTICLE_FILE.read_text(encoding="utf-8").strip() + "\n"
    missing = [heading for heading in REQUIRED_SECTIONS if heading not in body]
    if missing:
        raise ValueError(f"Missing required challenge sections: {missing}")
    if "39359492617" not in body:
        raise ValueError("Successful real-Gemma proof link is missing")
    if "TODO" in body:
        raise ValueError("Unresolved TODO in published entry")
    return body


def api_call(path: str, key: str, *, method: str = "GET", payload: dict | None = None) -> object:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = Request(
        API + path,
        data=data,
        headers={
            "api-key": key,
            "Accept": "application/vnd.forem.api-v1+json",
            "Content-Type": "application/json",
            "User-Agent": "QuietOps-Week3-Submission/1.0",
        },
        method=method,
    )
    try:
        with urlopen(req, timeout=35) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"DEV API returned HTTP {exc.code} for {method} {path}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"DEV API unavailable or sent invalid response: {type(exc).__name__}") from exc


def find_existing(key: str) -> dict | None:
    # Check only the authenticated user's posts; never create duplicate entries.
    for page in range(1, 11):
        params = urlencode({"per_page": 100, "page": page})
        entries = api_call(f"/articles/me/all?{params}", key)
        if not isinstance(entries, list):
            raise RuntimeError("DEV returned an unexpected articles response")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("title") == ARTICLE_TITLE:
                return entry
        if len(entries) < 100:
            break
    return None


def publish(key: str, body: str) -> str:
    existing = find_existing(key)
    if existing and existing.get("published"):
        link = str(existing.get("url", ""))
        if not link.startswith("https://dev.to/"):
            raise RuntimeError("Existing published DEV article did not return a valid URL")
        print(f"Already published; no duplicate created: {link}")
        return link

    fields = {
        "title": ARTICLE_TITLE,
        "body_markdown": body,
        "tags": TAGS,
        "published": True,
    }
    if existing:
        article_id = existing.get("id")
        if not isinstance(article_id, int):
            raise RuntimeError("Existing draft lacks a valid article ID")
        response = api_call(f"/articles/{article_id}", key, method="PUT", payload={"article": fields})
    else:
        response = api_call("/articles", key, method="POST", payload={"article": fields})

    if not isinstance(response, dict) or not response.get("published"):
        raise RuntimeError("DEV did not confirm a published article")
    link = response.get("url", "")
    if not isinstance(link, str) or not link.startswith("https://dev.to/"):
        raise RuntimeError("DEV did not provide a valid published-article URL")
    print(f"Published DEV challenge entry: {link}")
    return link


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="validate article; no API calls")
    args = parser.parse_args()
    try:
        body = article_body()
        if args.dry_run:
            print(f"Article ready: {ARTICLE_TITLE}")
            print(f"{len(body.split())} words; {len(TAGS)} tags; all required sections present")
            return 0
        key = os.environ.get("DEVTO_API_KEY", "").strip()
        if not key:
            raise RuntimeError("Missing DEVTO_API_KEY GitHub Actions secret; NO post was submitted")
        link = publish(key, body)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write(f"DEV competition entry published: {link}\n")
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Submission blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
