from __future__ import annotations

import concurrent.futures
import html
import json
import re
import ssl
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid"
AUTOMATION_DIR = Path(__file__).resolve().parent
DIRECTORY_FILE = AUTOMATION_DIR / "lff_church_directory.tsv"
SOURCE_FILES = [
    AUTOMATION_DIR / "podcast_sources.tsv",
    AUTOMATION_DIR / "lff_church_sources.tsv",
]
REPORT_PATH = BASE / "99_Index" / "LFF_Church_Sermon_Audit.md"
JSON_REPORT_PATH = BASE / "99_Index" / "lff_church_sermon_audit.json"

USER_AGENT = "BibleStudyAid/1.0 (+local source inventory)"
KEYWORDS = re.compile(
    r"sermon|message|media|watch|listen|podcast|audio|teaching|preach|archive",
    re.IGNORECASE,
)
FEED_HINT = re.compile(r"rss|feed|podcast|atom|\.xml(?:$|\?)", re.IGNORECASE)
MEDIA_HINT = re.compile(
    r"<audio\b|<video\b|youtube\.com|youtu\.be|vimeo\.com|sermonaudio|"
    r"sermoncloud|podbean|spotify\.com/(?:show|episode)|anchor\.fm|"
    r"\.mp3(?:[?\"'])|\.m4a(?:[?\"'])|\.mp4(?:[?\"'])",
    re.IGNORECASE,
)

EXISTING_CHURCH_SOURCE_MAP = {
    ("Georgia", "Greater Hope Baptist Church"): ["Greater_Hope_Baptist_Church"],
    ("Kansas", "Harvest Baptist Church"): ["Harvest_Baptist_Church_Messages"],
    ("Missouri", "Harvest Baptist Church"): ["Harvest_Baptist_Church_Of_Blue_Springs"],
    ("Missouri", "Heartland Baptist Fellowship"): ["Heartland_Baptist_Fellowship"],
    ("Missouri", "Midtown Baptist Temple"): [
        "Faith_Fellowship_Sermons",
        "Whole_Heart_Fellowship_Sermons",
        "Life_Fellowship_Sermons",
        "Midtown_Baptist_Temple_Audio",
    ],
    ("Ohio", "First Baptist Church of New Philadelphia"): [
        "First_Baptist_Church_Of_New_Philadelphia"
    ],
}

EXCLUDED_CHURCHES = {
    ("Wyoming", "High Plains Christian Fellowship"):
        "Excluded by owner request; personal sermon notes are already indexed separately.",
}


@dataclass
class PageLinks:
    links: list[tuple[str, str]] = field(default_factory=list)
    feeds: list[str] = field(default_factory=list)
    media: list[str] = field(default_factory=list)


class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.result = PageLinks()
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a" and values.get("href"):
            self._href = urljoin(self.base_url, values["href"])
            self._text = []
            if MEDIA_HINT.search(self._href):
                self.result.media.append(self._href)
        if tag.lower() in {"iframe", "audio", "video", "source"} and values.get("src"):
            source = urljoin(self.base_url, values["src"])
            if MEDIA_HINT.search(source):
                self.result.media.append(source)
        if tag.lower() == "link" and values.get("href"):
            rel = values.get("rel", "").lower()
            mime = values.get("type", "").lower()
            if "alternate" in rel and ("rss" in mime or "atom" in mime or "xml" in mime):
                self.result.feeds.append(urljoin(self.base_url, values["href"]))

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            text = re.sub(r"\s+", " ", " ".join(self._text)).strip()
            self.result.links.append((self._href, text))
            self._href = ""
            self._text = []


@dataclass
class FetchResult:
    requested_url: str
    final_url: str = ""
    content_type: str = ""
    text: str = ""
    error: str = ""


@dataclass
class ChurchAudit:
    region: str
    church: str
    website: str
    status: str
    sermon_pages: list[str] = field(default_factory=list)
    verified_feeds: list[str] = field(default_factory=list)
    media_pages: list[str] = field(default_factory=list)
    media_links: list[str] = field(default_factory=list)
    existing_sources: list[str] = field(default_factory=list)
    note: str = ""


def fetch(url: str, timeout: int = 14) -> FetchResult:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.7"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            body = response.read(4_000_000)
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchResult(
                requested_url=url,
                final_url=response.geturl(),
                content_type=content_type,
                text=body.decode(charset, errors="replace"),
            )
    except HTTPError as exc:
        return FetchResult(url, error=f"HTTP {exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return FetchResult(url, error=str(reason)[:160])


def parse_links(page: FetchResult) -> PageLinks:
    parser = LinkParser(page.final_url or page.requested_url)
    try:
        parser.feed(page.text)
    except Exception:
        pass
    return parser.result


def normalized_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = html.unescape(value).strip()
        key = clean.rstrip("/").lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def looks_like_feed(page: FetchResult) -> bool:
    sample = page.text[:500_000].lower()
    if not (("<rss" in sample or "<feed" in sample) and ("<item" in sample or "<entry" in sample)):
        return False
    return bool(
        re.search(r"<enclosure\b[^>]+(?:audio|video|\.mp3|\.m4a|\.mp4)", sample)
        or re.search(r"<media:content\b[^>]+(?:audio|video|\.mp3|\.m4a|\.mp4)", sample)
        or re.search(r"https?://[^<\"']+\.(?:mp3|m4a|mp4)(?:[?<\"'])", sample)
    )


def load_directory() -> list[tuple[str, str, str]]:
    records = []
    for raw_line in DIRECTORY_FILE.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.startswith("#"):
            continue
        parts = raw_line.split("\t")
        if len(parts) >= 2:
            records.append((parts[0].strip(), parts[1].strip(), parts[2].strip() if len(parts) > 2 else ""))
    return records


def load_existing_sources() -> list[tuple[str, str]]:
    sources = []
    for path in SOURCE_FILES:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parts = raw_line.split("|")
            if len(parts) >= 3 and not raw_line.startswith("#"):
                sources.append((parts[0].strip(), parts[2].strip()))
    return sources


def audit_church(record: tuple[str, str, str], existing: list[tuple[str, str]]) -> ChurchAudit:
    region, church, website = record
    if (region, church) in EXCLUDED_CHURCHES:
        return ChurchAudit(
            region,
            church,
            website,
            "excluded",
            note=EXCLUDED_CHURCHES[(region, church)],
        )
    if not website:
        return ChurchAudit(region, church, website, "no_website", note="The LFF directory does not provide a website link.")

    existing_matches = list(EXISTING_CHURCH_SOURCE_MAP.get((region, church), []))
    website_host = normalized_host(website)
    church_key = re.sub(r"[^a-z0-9]+", "", church.lower())
    for name, url in existing:
        if website_host and website_host == normalized_host(url):
            existing_matches.append(name)
        elif name.startswith("LFF_"):
            source_key = re.sub(r"[^a-z0-9]+", "", name[4:].lower())
            if church_key and (church_key in source_key or source_key in church_key):
                existing_matches.append(name)

    home = fetch(website)
    if home.error:
        return ChurchAudit(region, church, website, "unreachable", existing_sources=unique(existing_matches), note=home.error)

    home_links = parse_links(home)
    feed_candidates = list(home_links.feeds)
    page_candidates: list[str] = []
    home_host = normalized_host(home.final_url or website)
    for href, text in home_links.links:
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        combined = f"{href} {text}"
        if FEED_HINT.search(combined):
            feed_candidates.append(href)
        if KEYWORDS.search(combined) and normalized_host(href) == home_host:
            page_candidates.append(href)

    page_candidates = unique(page_candidates)[:4]
    media_pages = [home.final_url or website] if home_links.media else []
    media_links = list(home_links.media)

    for candidate in page_candidates:
        page = fetch(candidate)
        if page.error:
            continue
        links = parse_links(page)
        feed_candidates.extend(links.feeds)
        for href, text in links.links:
            if FEED_HINT.search(f"{href} {text}"):
                feed_candidates.append(href)
        if links.media:
            media_pages.append(page.final_url or candidate)
            media_links.extend(links.media)

    verified_feeds = []
    for candidate in unique(feed_candidates)[:8]:
        page = fetch(candidate)
        if not page.error and looks_like_feed(page):
            verified_feeds.append(page.final_url or candidate)

    verified_feeds = unique(verified_feeds)
    media_pages = unique(media_pages)
    media_links = unique(media_links)
    if verified_feeds:
        status = "verified_feed"
    elif media_links:
        status = "media_page"
    elif page_candidates:
        status = "sermon_page"
    else:
        status = "no_archive_found"

    return ChurchAudit(
        region,
        church,
        home.final_url or website,
        status,
        sermon_pages=page_candidates,
        verified_feeds=verified_feeds,
        media_pages=media_pages,
        media_links=media_links,
        existing_sources=unique(existing_matches),
    )


def write_report(results: list[ChurchAudit]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1

    lines = [
        "# Living Faith Fellowship Church Sermon Audit",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "Authoritative directory: https://www.lffellowship.com/churches",
        f"Churches audited: {len(results)}",
        "",
        "## Summary",
        "",
    ]
    labels = {
        "verified_feed": "Verified podcast/RSS feeds",
        "media_page": "Media pages requiring a site-specific importer",
        "sermon_page": "Sermon pages found without directly detectable media",
        "no_archive_found": "No sermon archive found from the public website",
        "unreachable": "Website unavailable during audit",
        "no_website": "No website supplied by the LFF directory",
        "excluded": "Excluded from intake",
    }
    for status, label in labels.items():
        lines.append(f"- {label}: {counts.get(status, 0)}")

    lines.extend([
        "",
        "## Results",
        "",
        "| Region | Church | Result | Existing source | Best sermon source |",
        "|---|---|---|---|---|",
    ])
    for item in results:
        best = (item.verified_feeds or item.media_links or item.sermon_pages or [item.website or item.note])[0]
        existing = ", ".join(item.existing_sources)
        lines.append(
            f"| {item.region} | {item.church} | {labels.get(item.status, item.status)} | {existing} | {best} |"
        )

    lines.extend(["", "## Verified New Feed Candidates", ""])
    existing_names = {name for item in results for name in item.existing_sources}
    candidates = [item for item in results if item.verified_feeds and not item.existing_sources]
    if candidates:
        for item in candidates:
            for feed in item.verified_feeds:
                lines.append(f"- {item.church} ({item.region}): {feed}")
    else:
        lines.append("- None found in this audit.")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    JSON_REPORT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "directory": "https://www.lffellowship.com/churches",
                "churches": [asdict(item) for item in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    records = load_directory()
    existing = load_existing_sources()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(audit_church, record, existing) for record in records]
        results = [future.result() for future in futures]
    write_report(results)
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status] = counts.get(item.status, 0) + 1
    print(f"Audited LFF churches: {len(results)}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
