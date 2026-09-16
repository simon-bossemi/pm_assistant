import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "pm_assistant_sdk_benchmark/1.0 (+internal benchmark; contact: pm_assistant)"


KEYWORD_HINTS = [
    "install",
    "installation",
    "setup",
    "getting-started",
    "get-started",
    "quick-start",
    "requirements",
    "prerequisites",
    "troubleshoot",
    "troubleshooting",
    "known-issues",
    "faq",
    "uninstall",
    "upgrade",
    "download",
    "sdk-manager",
    "docker",
    "proxy",
    "offline",
    "verify",
    "validation",
    "sample",
]


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())
    return s[:160] or "page"


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    fragmentless = parsed._replace(fragment="")
    return fragmentless.geturl()


def _same_domain(url: str, allowed_domains: set[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in allowed_domains)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)[:160]
    return ""


def _extract_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        href = href.strip()
        if not href or href.startswith(("mailto:", "javascript:", "#")):
            continue
        abs_url = _normalize_url(urljoin(base_url, href))
        if abs_url.startswith(("http://", "https://")):
            links.append(abs_url)
    return links


def _score_link_priority(url: str) -> int:
    lower = url.lower()
    score = 0
    for kw in KEYWORD_HINTS:
        if kw in lower:
            score += 5
    if lower.endswith((".pdf", ".zip", ".exe", ".dmg")):
        score -= 20
    return score


@dataclass
class Vendor:
    slug: str
    name: str
    start_urls: list[str]
    allowed_domains: set[str]


@dataclass
class Page:
    url: str
    status: int
    content_type: str
    title: str
    fetched_at: str
    raw_path: str
    text_path: str


def fetch_url(session: requests.Session, url: str) -> tuple[int, str, str]:
    resp = session.get(url, timeout=30, allow_redirects=True)
    status = resp.status_code
    ctype = resp.headers.get("content-type", "")
    html = resp.text if "text" in ctype or "html" in ctype or ctype == "" else ""
    return status, ctype, html


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def crawl_vendor(vendor: Vendor, out_dir: str, max_pages: int, polite_delay_s: float) -> list[Page]:
    vendor_dir = os.path.join(out_dir, vendor.slug)
    raw_dir = os.path.join(vendor_dir, "raw")
    text_dir = os.path.join(vendor_dir, "text")
    ensure_dir(raw_dir)
    ensure_dir(text_dir)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    seen: set[str] = set()
    queue: list[str] = []
    for u in vendor.start_urls:
        queue.append(_normalize_url(u))

    pages: list[Page] = []
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not _same_domain(url, vendor.allowed_domains):
            continue

        try:
            status, ctype, html = fetch_url(session, url)
        except Exception:
            continue

        fetched_at = time.strftime("%Y-%m-%d %H:%M:%S")
        base = _safe_filename(urlparse(url).path.strip("/").replace("/", "_") or vendor.slug)
        stem = f"{base}_{_sha1(url)[:10]}"
        raw_path = os.path.join(raw_dir, stem + ".html")
        text_path = os.path.join(text_dir, stem + ".txt")

        if html:
            with open(raw_path, "w", encoding="utf-8", newline="") as f:
                f.write(html)
            with open(text_path, "w", encoding="utf-8", newline="") as f:
                f.write(_extract_text(html))
            title = _extract_title(html)
            links = _extract_links(url, html)
        else:
            title = ""
            links = []

        pages.append(
            Page(
                url=url,
                status=status,
                content_type=ctype,
                title=title,
                fetched_at=fetched_at,
                raw_path=os.path.relpath(raw_path, out_dir),
                text_path=os.path.relpath(text_path, out_dir),
            )
        )

        candidates = [l for l in links if _same_domain(l, vendor.allowed_domains)]
        candidates.sort(key=_score_link_priority, reverse=True)
        for l in candidates[:50]:
            if l not in seen and l not in queue:
                queue.append(l)

        if polite_delay_s > 0:
            time.sleep(polite_delay_s)

    return pages


def default_vendors() -> list[Vendor]:
    return [
        Vendor(
            slug="qualcomm",
            name="Qualcomm QAIRT / QNN / Genie",
            start_urls=[
                "https://docs.qualcomm.com/doc/80-70018-15B/topic/qairt-install.html",
                "https://docs.qualcomm.com/nav/home/setup.html?product=1601111740010412",
            ],
            allowed_domains={"docs.qualcomm.com"},
        ),
        Vendor(
            slug="nvidia_jetson",
            name="NVIDIA Jetson / SDK Manager",
            start_urls=[
                "https://docs.nvidia.com/sdk-manager/install-with-sdkm-jetson/index.html",
                "https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit#setup",
                "https://developer.nvidia.com/embedded/learn/get-started-jetson-agx-orin-devkit",
                "https://developer.nvidia.com/sdk-manager",
            ],
            allowed_domains={"docs.nvidia.com", "developer.nvidia.com"},
        ),
        Vendor(
            slug="renesas_rzv_ai",
            name="Renesas RZ/V AI SDK",
            start_urls=[
                "https://renesas-rz.github.io/rzv_ai_sdk/7.00/getting_started.html#step5",
                "https://renesas-rz.github.io/rzv_ai_sdk/7.00/howto_build_aisdk.html",
                "https://renesas-rz.github.io/rzv_ai_sdk/7.00/",
            ],
            allowed_domains={"renesas-rz.github.io"},
        ),
        Vendor(
            slug="quadric",
            name="Quadric Chimera SDK",
            start_urls=[
                "https://app.quadric.ai/docs/latest/chimera-software-user-guide/chimera-sdk-quick-start-guide",
            ],
            allowed_domains={"app.quadric.ai"},
        ),
        Vendor(
            slug="tenstorrent",
            name="Tenstorrent (docs + tt-installer)",
            start_urls=[
                "https://docs.tenstorrent.com/getting-started/README.html",
                "https://github.com/tenstorrent/tt-installer",
            ],
            allowed_domains={"docs.tenstorrent.com", "github.com"},
        ),
        Vendor(
            slug="rockchip_rknn",
            name="Rockchip RKNN SDK",
            start_urls=[
                # Seed with common public entry points; refined later in report generation.
                "https://github.com/rockchip-linux/rknn-toolkit2",
                "https://github.com/rockchip-linux/rknn-toolkit",
            ],
            allowed_domains={"github.com"},
        ),
        Vendor(
            slug="bos",
            name="BOS SDK (Host setup)",
            start_urls=[
                "http://192.128.10.230/bos-sdk/docs/Host%20Machine%20Setup/",
            ],
            allowed_domains={"192.128.10.230"},
        ),
    ]


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Collect SDK installation docs for benchmark reporting.")
    parser.add_argument("--out", required=True, help="Output directory to store crawled pages + index.json")
    parser.add_argument("--max-pages", type=int, default=18, help="Max pages per vendor (default: 18)")
    parser.add_argument("--delay", type=float, default=0.25, help="Polite delay (seconds) between requests")
    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = os.path.abspath(args.out)
    ensure_dir(out_dir)

    index: dict[str, object] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_agent": USER_AGENT,
        "max_pages_per_vendor": args.max_pages,
        "vendors": [],
    }

    vendors = default_vendors()
    for vendor in vendors:
        pages = crawl_vendor(vendor, out_dir, max_pages=args.max_pages, polite_delay_s=args.delay)
        index["vendors"].append(
            {
                "vendor": {
                    "slug": vendor.slug,
                    "name": vendor.name,
                    "start_urls": vendor.start_urls,
                    "allowed_domains": sorted(vendor.allowed_domains),
                },
                "pages": [asdict(p) for p in pages],
            }
        )

    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
