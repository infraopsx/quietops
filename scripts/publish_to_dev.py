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
    if "https://infraopsx.github.io/quietops/" not in body:
        raise ValueError("Public model-backed browser demo link is missing")
    if "https://github.com/infraopsx/quietops/actions/workflows/live-gemma.yml" not in body:
        raise ValueError("Real-Gemma workflow proof link is missing")
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


def _is_published(article: dict) -> bool:
    # Forem's public article serializer usually omits "published" and exposes
    # "published_at" instead. A missing boolean is NOT evidence of a draft.
    return (
        article.get("published") is True
        or bool(article.get("published_at"))
        or bool(article.get("published_timestamp"))
    )


def _article_tags(article: dict) -> set[str]:
    tags = article.get("tag_list")
    if isinstance(tags, list):
        return {tag.strip().lower() for tag in tags if isinstance(tag, str)}
    raw = article.get("tags", "")
    return {tag.strip().lower() for tag in raw.split(",")} if isinstance(raw, str) else set()


def _has_challenge_tags(article: dict) -> bool:
    return {"devchallenge", "hf26challenge"}.issubset(_article_tags(article))


def _published_url(article: dict) -> str:
    url = article.get("url", "")
    if not isinstance(url, str) or not url.startswith("https://dev.to/"):
        raise RuntimeError("Published article has no trustworthy DEV URL")
    return url


def _get_remote_body(key: str, article_id: int) -> str:
    """Read the actual published Markdown; never infer sync from tags alone."""
    remote = api_call(f"/articles/{article_id}", key)
    if not isinstance(remote, dict) or not isinstance(remote.get("body_markdown"), str):
        raise RuntimeError("DEV did not return readable body_markdown; stopped instead of guessing")
    return remote["body_markdown"].strip()


def publish(key: str, body: str) -> str:
    existing = find_existing(key)
    article_id = existing.get("id") if existing else None
    if existing and not isinstance(article_id, int):
        raise RuntimeError("Existing DEV entry has no valid article ID; stopped to avoid duplicates")

    # Re-read the article body before deciding whether an update is needed.
    # Previously this function skipped all updates once the tags were correct.
    if existing and _is_published(existing) and _has_challenge_tags(existing):
        if _get_remote_body(key, article_id) == body.strip():
            link = _published_url(existing)
            print(f"Already published and article body matches repository: {link}")
            return link

    # DEV/Forem tags are a comma-separated string, NOT a JSON array.
    fields = {
        "title": ARTICLE_TITLE,
        "body_markdown": body,
        "tags": ", ".join(TAGS),
        "published": True,
    }
    if existing:
        response = api_call(f"/articles/{article_id}", key, method="PUT", payload={"article": fields})
        operation = "Updated existing"
    else:
        response = api_call("/articles", key, method="POST", payload={"article": fields})
        operation = "Created"

    if not isinstance(response, dict):
        raise RuntimeError("DEV returned an unexpected article object")

    # Re-read the account and content. This confirms the actual post, tags,
    # and updated Markdown without exposing DEVTO_API_KEY or making duplicates.
    verified = find_existing(key)
    if verified and _is_published(verified) and _has_challenge_tags(verified):
        verified_id = verified.get("id")
        if not isinstance(verified_id, int):
            raise RuntimeError("Published DEV entry has no integer ID")
        link = _published_url(verified)
        if _get_remote_body(key, verified_id) != body.strip():
            raise RuntimeError(
                f"DEV article is published but body does not match submitted Markdown: {link}"
            )
        print(f"{operation} and verified published DEV challenge article with matching body: {link}")
        return link

    returned_id = response.get("id", article_id)
    returned_tags = sorted(_article_tags(response))
    print(
        f"DEV returned article ID={returned_id}; tags={returned_tags}. "
        "No duplicate will be created on a later run.",
        file=sys.stderr,
    )
    raise RuntimeError(
        "Article exists on DEV but publication/tags could not be confirmed; "
        "check https://dev.to/dashboard"
    )


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
