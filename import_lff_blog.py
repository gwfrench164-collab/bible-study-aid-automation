from pathlib import Path
import re
import hashlib
from pipeline_support import atomic_write_text
from library_settings import LIBRARY_ROOT
import re
import hashlib
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.lffellowship.com"
BLOG_URL = "https://www.lffellowship.com/blog"
DEST = LIBRARY_ROOT / "06_Blogs" / "Living_Faith_Fellowship"

HEADERS = {
    "User-Agent": "BibleStudyAid/1.0"
}

def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text[:120]

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def collect_post_links():
    pages_to_visit = [BLOG_URL]
    visited_pages = set()
    post_links = set()

    while pages_to_visit:
        page_url = pages_to_visit.pop(0)
        if page_url in visited_pages:
            continue
        visited_pages.add(page_url)

        soup = get_soup(page_url)

        # Collect only actual post links from title links and "Read More" links.
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)

            if href.startswith("/"):
                href = BASE_URL + href
            elif not href.startswith("http"):
                continue

            # Squarespace blog post URLs live under /blog/<slug>
            # but skip the archive page itself.
            if "/blog/" in href and not href.rstrip("/").endswith("/blog"):
                if text == "Read More" or a.find_parent(["h1", "h2", "h3"]):
                    post_links.add(href)

        # Follow the Older Posts pagination link if present.
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(" ", strip=True)
            href = a["href"]
            if link_text == "Older Posts":
                if href.startswith("/"):
                    href = BASE_URL + href
                elif not href.startswith("http"):
                    continue
                if href not in visited_pages:
                    pages_to_visit.append(href)

    return sorted(post_links)

def extract_text_from_post(url: str):
    soup = get_soup(url)

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    headings = soup.find_all(["h1", "h2", "h3"])
    if headings:
        title = headings[0].get_text(" ", strip=True) or title

    text_blocks = []
    article = soup.select_one(".blog-item-content, .entry-content, article") or soup
    for tag in article.find_all(["p", "li"]):
        text = tag.get_text(" ", strip=True)
        if text:
            text_blocks.append(text)

    body = "\n\n".join(text_blocks)
    return title, body

def main():
    DEST.mkdir(parents=True, exist_ok=True)

    existing_urls = set()
    for path in DEST.glob("*.txt"):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:8]:
            if line.startswith("URL: "):
                existing_urls.add(line[5:].strip().rstrip("/"))
    failures = 0
    links = collect_post_links()
    print(f"Found {len(links)} blog post links.")

    for url in links:
        if url.rstrip("/") in existing_urls:
            continue
        try:
            title, body = extract_text_from_post(url)
            if not body.strip():
                print(f"SKIP empty: {url}")
                continue

            safe_name = slugify(title or url.split("/")[-1])
            if safe_name.upper() == "LIVING_FAITH_BLOGS":
                print(f"SKIP archive page: {url}")
                continue
            out_file = DEST / f"{safe_name}.txt"

            if out_file.exists():
                out_file = DEST / f"{safe_name}_{hashlib.sha256(url.encode()).hexdigest()[:12]}.txt"

            content = f"Title: {title}\nURL: {url}\n\n{body}\n"
            atomic_write_text(out_file, content)
            print(f"WROTE: {out_file.name}")

        except Exception as e:
            failures += 1
            print(f"ERROR: {url} -> {e}")

    if failures:
        raise RuntimeError(f"{failures} blog imports failed")
    print("LFF blog import complete.")

if __name__ == "__main__":
    main()