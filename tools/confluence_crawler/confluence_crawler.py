from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

VENDOR_DIR = Path(__file__).with_name("vendor")
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = ROOT / "wiki"
DEFAULT_DOTENV_PATH = Path(__file__).with_name(".env")


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or fallback


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid Confluence URL: {value}")

    path = parsed.path or ""
    wiki_index = path.find("/wiki")
    if wiki_index >= 0:
        path = path[: wiki_index + len("/wiki")]
    else:
        path = "/wiki"

    return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")


def site_slug(base_url: str) -> str:
    parsed = urlparse(base_url)
    path = parsed.path.strip("/").replace("/", "_")
    raw = parsed.netloc if not path else f"{parsed.netloc}_{path}"
    return slugify(raw, fallback="confluence-site")


def extract_text_blocks(storage_html: str) -> list[str]:
    soup = BeautifulSoup(storage_html or "", "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    blocks: list[str] = []
    for tag in soup.find_all(
        ["h1", "h2", "h3", "h4", "p", "li", "pre", "code", "th", "td"]
    ):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if not text:
            continue

        if tag.name in {"h1", "h2", "h3", "h4"}:
            blocks.append(f"## {text}")
            continue

        if tag.name == "li":
            blocks.append(f"- {text}")
            continue

        blocks.append(text)

    deduped: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        if block in seen:
            continue
        deduped.append(block)
        seen.add(block)

    return deduped


def extract_headings(blocks: Iterable[str]) -> list[str]:
    headings: list[str] = []
    for block in blocks:
        if not block.startswith("## "):
            continue
        heading = block[3:].strip()
        if heading:
            headings.append(heading)
    return headings


def summarize_text(text: str, headings: list[str], limit: int = 5) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    candidates: list[str] = []

    for heading in headings[:2]:
        candidates.append(f"Section present: {heading}.")

    for sentence in sentences:
        cleaned = " ".join(sentence.split())
        if len(cleaned) < 50:
            continue
        if cleaned in candidates:
            continue
        candidates.append(cleaned)
        if len(candidates) >= limit:
            break

    if not candidates and text.strip():
        fallback = " ".join(text.split())[:300].strip()
        if fallback:
            candidates.append(fallback)

    return candidates[:limit]


@dataclass
class CrawlConfig:
    base_url: str
    email: str
    api_token: str
    output_root: Path
    max_pages: int
    page_ids: list[str]
    space_key: str | None
    ancestor_id: str | None
    delay_seconds: float


class ConfluenceCrawler:
    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.trust_env = (
            os.getenv("CONFLUENCE_TRUST_ENV_PROXY", "false").strip().lower()
            in {"1", "true", "yes"}
        )
        self.session.auth = (config.email, config.api_token)
        self.session.headers.update({"Accept": "application/json"})
        self.base_api_url = f"{config.base_url}/rest/api"
        self.site_dir = config.output_root / site_slug(config.base_url)
        self.pages_dir = self.site_dir / "pages"

    def crawl(self) -> dict:
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        page_refs = self._resolve_page_refs()

        manifest = {
            "base_url": self.config.base_url,
            "space_key": self.config.space_key,
            "ancestor_id": self.config.ancestor_id,
            "requested_max_pages": self.config.max_pages,
            "page_count": 0,
            "pages": [],
        }

        for index, page_ref in enumerate(page_refs, start=1):
            page = self._fetch_page(page_ref["id"])
            record = self._build_page_record(page)

            slug = f'{record["id"]}-{slugify(record["title"], fallback="page")}'
            json_path = self.pages_dir / f"{slug}.json"
            md_path = self.pages_dir / f"{slug}.md"

            json_path.write_text(
                json.dumps(record, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
            md_path.write_text(self._render_markdown(record), encoding="utf-8")

            manifest["pages"].append(
                {
                    "id": record["id"],
                    "title": record["title"],
                    "url": record["url"],
                    "updated_at": record["updated_at"],
                    "space": record["space"],
                    "json_path": str(json_path.relative_to(self.site_dir)),
                    "markdown_path": str(md_path.relative_to(self.site_dir)),
                }
            )

            if self.config.delay_seconds > 0 and index < len(page_refs):
                time.sleep(self.config.delay_seconds)

        manifest["page_count"] = len(manifest["pages"])

        manifest_path = self.site_dir / "crawl_manifest.json"
        summary_path = self.site_dir / "summary.md"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        summary_path.write_text(self._render_summary(manifest), encoding="utf-8")
        return {
            "manifest_path": str(manifest_path),
            "summary_path": str(summary_path),
            "page_count": manifest["page_count"],
        }

    def _resolve_page_refs(self) -> list[dict]:
        if self.config.page_ids:
            return [{"id": page_id} for page_id in self.config.page_ids]

        cql_parts = ["type = page"]
        if self.config.space_key:
            cql_parts.append(f'space = "{self.config.space_key}"')
        if self.config.ancestor_id:
            cql_parts.append(f"ancestor = {self.config.ancestor_id}")
        cql = " and ".join(cql_parts) + " order by lastmodified desc"

        page_refs: list[dict] = []
        start = 0
        page_size = min(self.config.max_pages, 50)

        while len(page_refs) < self.config.max_pages:
            response = self.session.get(
                f"{self.base_api_url}/search",
                params={"cql": cql, "limit": page_size, "start": start},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            if not results:
                break

            for result in results:
                content = result.get("content") or {}
                page_id = content.get("id")
                if not page_id:
                    continue
                page_refs.append({"id": str(page_id)})
                if len(page_refs) >= self.config.max_pages:
                    break

            if not payload.get("_links", {}).get("next"):
                break
            start += len(results)

        return page_refs

    def _fetch_page(self, page_id: str) -> dict:
        response = self.session.get(
            f"{self.base_api_url}/content/{page_id}",
            params={
                "expand": ",".join(
                    [
                        "body.storage",
                        "version",
                        "space",
                        "ancestors",
                    ]
                )
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _build_page_record(self, page: dict) -> dict:
        storage_html = (
            page.get("body", {})
            .get("storage", {})
            .get("value", "")
        )
        blocks = extract_text_blocks(storage_html)
        plain_text = "\n".join(blocks)
        headings = extract_headings(blocks)
        links = page.get("_links", {})
        webui = links.get("webui", "")
        url = f"{self.config.base_url}{webui}" if webui.startswith("/") else webui

        return {
            "id": page.get("id"),
            "title": page.get("title"),
            "type": page.get("type"),
            "space": (page.get("space") or {}).get("key"),
            "updated_at": (page.get("version") or {}).get("when"),
            "url": url,
            "ancestors": [
                {
                    "id": ancestor.get("id"),
                    "title": ancestor.get("title"),
                }
                for ancestor in (page.get("ancestors") or [])
            ],
            "headings": headings,
            "summary_points": summarize_text(plain_text, headings),
            "text": plain_text,
            "storage_html": storage_html,
        }

    def _render_markdown(self, record: dict) -> str:
        lines = [
            f"# {record['title']}",
            "",
            f"- Page ID: {record['id']}",
            f"- Space: {record['space'] or 'unknown'}",
            f"- Updated: {record['updated_at'] or 'unknown'}",
            f"- URL: {record['url'] or 'unavailable'}",
            "",
            "## Useful Information",
        ]

        if record["summary_points"]:
            lines.extend(f"- {point}" for point in record["summary_points"])
        else:
            lines.append("- No high-confidence summary points were extracted.")

        if record["headings"]:
            lines.extend(["", "## Headings"])
            lines.extend(f"- {heading}" for heading in record["headings"])

        lines.extend(["", "## Extracted Text", record["text"] or "(no text extracted)"])
        lines.append("")
        return "\n".join(lines)

    def _render_summary(self, manifest: dict) -> str:
        lines = [
            "# Confluence Crawl Summary",
            "",
            f"- Base URL: {manifest['base_url']}",
            f"- Space key filter: {manifest['space_key'] or 'none'}",
            f"- Ancestor filter: {manifest['ancestor_id'] or 'none'}",
            f"- Pages captured: {manifest['page_count']}",
            "",
            "## Pages",
        ]

        if not manifest["pages"]:
            lines.append("- No pages were returned by the current query.")
        else:
            for page in manifest["pages"]:
                lines.append(
                    f"- {page['title']} ({page['id']}): {page['markdown_path']}"
                )

        lines.append("")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl Confluence Cloud pages and save useful extracted content."
    )
    parser.add_argument("--base-url", help="Confluence base URL, e.g. https://example.atlassian.net/wiki")
    parser.add_argument("--email", help="Atlassian account email")
    parser.add_argument("--api-token", help="Atlassian API token")
    parser.add_argument("--space-key", help="Optional Confluence space key filter")
    parser.add_argument("--ancestor-id", help="Optional ancestor page ID filter")
    parser.add_argument(
        "--page-id",
        dest="page_ids",
        action="append",
        default=[],
        help="Specific page ID to fetch. Repeat to fetch multiple pages.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to fetch when using search mode.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=None,
        help="Delay between page fetches to be gentle on the API.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory where crawl output will be written.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> CrawlConfig:
    load_dotenv(DEFAULT_DOTENV_PATH, override=False)

    base_url = args.base_url or os.getenv("CONFLUENCE_BASE_URL")
    email = args.email or os.getenv("CONFLUENCE_EMAIL")
    api_token = args.api_token or os.getenv("CONFLUENCE_API_TOKEN")
    max_pages = args.max_pages or int(os.getenv("CONFLUENCE_MAX_PAGES", "25"))
    delay_seconds = (
        args.delay_seconds
        if args.delay_seconds is not None
        else float(os.getenv("CONFLUENCE_DELAY_SECONDS", "0.2"))
    )
    output_root = args.output_root or Path(
        os.getenv("CONFLUENCE_OUTPUT_ROOT", str(DEFAULT_OUTPUT_ROOT))
    )
    space_key = args.space_key or os.getenv("CONFLUENCE_SPACE_KEY")
    ancestor_id = args.ancestor_id or os.getenv("CONFLUENCE_ANCESTOR_ID")

    missing = [
        name
        for name, value in [
            ("CONFLUENCE_BASE_URL", base_url),
            ("CONFLUENCE_EMAIL", email),
            ("CONFLUENCE_API_TOKEN", api_token),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            "Missing required configuration: " + ", ".join(missing)
        )

    if max_pages < 1:
        raise ValueError("--max-pages must be at least 1")

    return CrawlConfig(
        base_url=normalize_base_url(base_url),
        email=email,
        api_token=api_token,
        output_root=output_root,
        max_pages=max_pages,
        page_ids=args.page_ids,
        space_key=space_key,
        ancestor_id=ancestor_id,
        delay_seconds=delay_seconds,
    )


def main() -> int:
    try:
        config = build_config(parse_args())
        result = ConfluenceCrawler(config).crawl()
    except requests.HTTPError as exc:
        response = exc.response
        status = response.status_code if response is not None else "unknown"
        body = response.text[:500] if response is not None else str(exc)
        print(f"Confluence request failed ({status}): {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
