#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""Sync the official LangChain / LangGraph / Deep Agents / LangSmith docs into ``harness/docs``.

The public docs site (docs.langchain.com, Mintlify) exposes every page as plain
markdown by appending ``.md`` to the page URL.  That is the format recommended for
LLM consumption, so we mirror those files locally::

    harness/docs/
      llms.txt                     # local index, entry point for AI tooling
      MANIFEST.json                # url / sha256 / size / fetch timestamp
      _official/_llms/**.txt       # upstream llms.txt index tree (provenance)
      oss/python/langchain/**.md
      oss/python/langgraph/**.md
      oss/python/deepagents/**.md
      oss/python/integrations/**.md
      langsmith/python/**.md       # Managed Deep Agents
      langsmith/fleet/**.md
      ...

Usage:
    python harness/scripts/fetch_docs.py            # sync (skip unchanged)
    python harness/scripts/fetch_docs.py --check    # verify local copy
    python harness/scripts/fetch_docs.py --index-only
    python harness/scripts/fetch_docs.py --include oss/javascript/langgraph
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://docs.langchain.com"
ROOT = Path(__file__).resolve().parents[1] / "docs"
OFFICIAL_DIR = ROOT / "_official"
INDEX_DIR = OFFICIAL_DIR / "_llms"

# Paths to mirror.  A trailing "*" enables glob matching, an exact path matches
# the page itself.
DEFAULT_PREFIXES = (
    # LangChain / LangGraph (Python)
    "oss/python/langchain",
    "oss/python/langgraph",
    "oss/python/concepts",
    "oss/python/reference",
    "oss/python/migrate",
    "oss/python/releases",
    "oss/python/common-errors",
    "oss/python/learn",
    # Deep Agents
    "oss/python/deepagents",
    "oss/deepagents/code",
    "oss/openwiki",
    # LangChain integrations
    "oss/python/integrations",
    # Managed Deep Agents (LangSmith)
    "langsmith/python/managed-deep-agents-*",
    "langsmith/manage-contexts-sdk",
    "langsmith/use-the-context-hub",
    # LangSmith Fleet
    "langsmith/fleet",
    # LangSmith core for agent builders
    "langsmith/observability*",
    "langsmith/deployment*",
    "langsmith/evaluation*",
    "langsmith/studio",
    "langsmith/trace-with-langchain",
    "langsmith/trace-with-langgraph",
    "langsmith/trace-deep-agents",
    "langsmith/trace-with-opencode",
    "langsmith/trace-with-codex",
    "langsmith/trace-claude-code",
    "langsmith/trace-claude-agent-sdk",
    # How AI coding tools are meant to consume the docs
    "use-these-docs",
)

USER_AGENT = "nonstop-harness-docs-sync/1.0 (+https://docs.langchain.com)"

INDEX_LINE = re.compile(r"^-\s*\[(?P<title>.*?)\]\((?P<url>[^)\s]+)\)\s*:?\s*(?P<description>.*)$")


@dataclass
class Page:
    url: str          # canonical page URL, e.g. https://docs.langchain.com/oss/python/langgraph/overview
    path: str         # local relative path, e.g. oss/python/langgraph/overview.md
    title: str
    description: str


def fetch(url: str, timeout: int = 60, retries: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (404, 410):
                raise
            last_error = error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def parse_index(text: str) -> list[tuple[str, str, str]]:
    """Parse a Mintlify llms.txt index into (url, title, description) tuples."""
    entries = []
    for line in text.splitlines():
        match = INDEX_LINE.match(line.strip())
        if not match:
            continue
        description = match.group("description").strip()
        if description.endswith("."):
            description = description[:-1]
        entries.append((match.group("url"), match.group("title").strip(), description))
    return entries


def crawl_indexes() -> dict[str, tuple[str, str]]:
    """Walk the upstream /_llms/ index tree and return {route: (title, description)}."""
    catalogue: dict[str, tuple[str, str]] = {}
    queue = [f"{BASE}/llms.txt"]
    visited: set[str] = set()
    while queue:
        index_url = queue.pop(0)
        if index_url in visited:
            continue
        visited.add(index_url)
        try:
            data = fetch(index_url)
        except RuntimeError:
            continue
        text = data.decode("utf-8", errors="replace")
        local = INDEX_DIR / index_url.removeprefix(f"{BASE}/")
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
        for url, title, description in parse_index(text):
            if url.startswith(f"{BASE}/"):
                route = url.removeprefix(f"{BASE}/").removesuffix(".md")
                catalogue.setdefault(route, (title, description))
                if url.endswith(".txt"):
                    queue.append(url)
    return catalogue


def sitemap_routes() -> dict[str, tuple[str, str]]:
    """Every published page, straight from the sitemap."""
    routes: dict[str, tuple[str, str]] = {}
    try:
        data = fetch(f"{BASE}/sitemap.xml").decode("utf-8", errors="replace")
    except RuntimeError:
        return routes
    for chunk in data.split("<loc>")[1:]:
        url = chunk.split("</loc>", 1)[0].strip()
        if url.startswith(f"{BASE}/"):
            route = url.removeprefix(f"{BASE}/").removesuffix(".md")
            routes.setdefault(route, ("", ""))
    return routes


def matches(route: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if "*" in pattern:
            if fnmatch.fnmatch(route, pattern):
                return True
        elif route == pattern or route.startswith(f"{pattern}/"):
            return True
    return False


def discover_pages(prefixes: tuple[str, ...]) -> list[Page]:
    """Collect every page URL under the requested path patterns."""
    catalogue = crawl_indexes()
    catalogue.update(sitemap_routes())

    pages = []
    for route, (title, description) in sorted(catalogue.items()):
        if not matches(route, prefixes):
            continue
        pages.append(
            Page(
                url=f"{BASE}/{route}",
                path=f"{route}.md",
                title=title or route.rsplit("/", 1)[-1],
                description=description,
            )
        )
    return pages


def download_page(page: Page, skip_existing: bool = False) -> tuple[Page, str, int]:
    """Download one page as markdown. Returns (page, sha256, bytes)."""
    target = ROOT / page.path
    if skip_existing and target.exists() and target.stat().st_size > 0:
        data = target.read_bytes()
        return page, hashlib.sha256(data).hexdigest(), len(data)
    data = fetch(f"{page.url}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return page, hashlib.sha256(data).hexdigest(), len(data)


def infer_title_and_description(page: Page, body: str) -> tuple[str, str]:
    """Fall back to parsing the markdown when the index had no metadata."""
    title = page.title
    description = page.description
    lines = body.splitlines()
    if not title:
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break
        else:
            title = page.path.rsplit("/", 1)[-1].removesuffix(".md")
    if not description:
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ">", "`", "|", "-", "*", "[")):
                continue
            description = stripped
            break
    return title, description


def group_of(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "root"
    if len(parts) <= 2:
        return parts[0]
    if parts[2].endswith(".md"):
        return "/".join(parts[:2])
    return "/".join(parts[:3])


def write_local_index(pages: list[Page]) -> Path:
    """Write harness/docs/llms.txt in the upstream llms.txt format."""
    index_path = ROOT / "llms.txt"
    groups: dict[str, list[Page]] = {}
    for page in pages:
        groups.setdefault(group_of(page.path), []).append(page)

    lines = [
        "# LangChain / LangGraph / Deep Agents / LangSmith official docs",
        "",
        "> Mirrored from https://docs.langchain.com for local AI tooling.",
        "> Last synced: " + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "",
    ]
    for group in sorted(groups):
        lines.append(f"## {group}")
        lines.append("")
        for page in sorted(groups[group], key=lambda item: item.path):
            entry = f"- [{page.title}]({page.path})"
            if page.description:
                entry += f": {page.description}"
            lines.append(entry)
        lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def write_manifest(pages: list[Page], digests: dict[str, tuple[str, int]]) -> Path:
    manifest_path = ROOT / "MANIFEST.json"
    entries = []
    for page in pages:
        sha, size = digests.get(page.path, ("", 0))
        entries.append(
            {
                "url": page.url,
                "path": page.path,
                "sha256": sha,
                "bytes": size,
                "title": page.title,
                "description": page.description,
            }
        )
    manifest_path.write_text(
        json.dumps(
            {
                "source": BASE,
                "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page_count": len(entries),
                "total_bytes": sum(item["bytes"] for item in entries),
                "pages": entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def load_manifest_pages() -> list[Page]:
    """Rebuild the page list from a previous run's manifest."""
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    return [
        Page(
            url=item["url"],
            path=item["path"],
            title=item.get("title", ""),
            description=item.get("description", ""),
        )
        for item in manifest["pages"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--include", action="append", default=[], metavar="PREFIX",
                        help="extra upstream path pattern to include, e.g. oss/javascript/langgraph")
    parser.add_argument("--workers", type=int, default=8, help="parallel downloads (default: 8)")
    parser.add_argument("--check", action="store_true", help="verify the local mirror, do not download")
    parser.add_argument("--skip-existing", action="store_true",
                        help="keep local files that already exist (fast incremental sync)")
    parser.add_argument("--index-only", action="store_true",
                        help="rebuild llms.txt / MANIFEST.json from the files already on disk")
    args = parser.parse_args()

    prefixes = tuple(DEFAULT_PREFIXES) + tuple(args.include)
    failures: list[tuple[str, str]] = []

    if args.check:
        pages = discover_pages(prefixes)
        missing = [page.path for page in pages if not (ROOT / page.path).exists()]
        empty = [page.path for page in pages if (ROOT / page.path).exists() and (ROOT / page.path).stat().st_size == 0]
        print(f"pages={len(pages)} missing={len(missing)} empty={len(empty)}")
        for path in missing + empty:
            print(f"  MISSING {path}")
        return 1 if (missing or empty) else 0

    if args.index_only:
        pages = load_manifest_pages()
        digests = {
            page.path: (
                hashlib.sha256((ROOT / page.path).read_bytes()).hexdigest(),
                (ROOT / page.path).stat().st_size,
            )
            for page in pages
            if (ROOT / page.path).exists()
        }
    else:
        pages = discover_pages(prefixes)
        print(f"discovered {len(pages)} pages matching {len(prefixes)} patterns")

        digests: dict[str, tuple[str, int]] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(download_page, page, args.skip_existing): page for page in pages}
            for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                page = futures[future]
                try:
                    page, sha, size = future.result()
                except Exception as error:  # noqa: BLE001
                    failures.append((page.path, str(error)))
                    continue
                digests[page.path] = (sha, size)
                print(f"[{index}/{len(pages)}] {page.path} ({size:,} bytes)")

    # Refresh titles/descriptions from the downloaded markdown when missing.
    for page in pages:
        path = ROOT / page.path
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        page.title, page.description = infer_title_and_description(page, body)

    index_path = write_local_index(pages)
    manifest_path = write_manifest(pages, digests)

    total = sum(size for _, size in digests.values())
    verb = "indexed" if args.index_only else "downloaded"
    print(f"index  -> {index_path.relative_to(ROOT.parent)}")
    print(f"manifest -> {manifest_path.relative_to(ROOT.parent)}")
    print(f"{verb} {len(digests)}/{len(pages)} pages, {total:,} bytes")

    if failures:
        print(f"FAILED {len(failures)} pages:", file=sys.stderr)
        for path, error in failures:
            print(f"  {path}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
