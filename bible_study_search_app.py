from pathlib import Path
import sys
import subprocess
import re
import threading
import time
import webbrowser
from copy import deepcopy
from flask import Flask, request, render_template_string, abort, Response
from html import escape
from urllib.parse import urlencode
from werkzeug.serving import make_server

AUTOMATION_DIR = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/98_Automation")
BASE = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid")
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

import query_bible_study as qbs
from transcript_reader import render_reader
from study_passages import narrow_results, register_shelf

app = Flask(__name__)
register_shelf(app, qbs)

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Bible Study Aid</title>
    <style>
        :root {
            --bg: #f6f7fb;
            --panel: #ffffff;
            --text: #1f2937;
            --muted: #6b7280;
            --line: #d1d5db;
            --accent: #1d4ed8;
            --accent-soft: #dbeafe;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
        }
        .page {
            max-width: 1400px;
            margin: 0 auto;
            padding: 18px;
        }
        .header {
            margin-bottom: 14px;
        }
        .header h1 {
            margin: 0 0 6px 0;
            font-size: 1.9rem;
        }
        .header p {
            margin: 0;
            color: var(--muted);
        }
        .search-panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 14px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .search-row {
            display: grid;
            grid-template-columns: minmax(280px, 1fr) 240px 145px 95px 110px;
            gap: 10px;
            align-items: start;
        }
        .field-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--muted);
        }
        .source-filter-box {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: #fff;
        }
        .source-filter-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px 12px;
        }
        .source-filter-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            color: var(--text);
        }
        .source-filter-item input {
            margin: 0;
        }
        input[type="text"], select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--line);
            border-radius: 10px;
            font-size: 1rem;
            background: #fff;
            color: var(--text);
        }
        button {
            width: 100%;
            padding: 11px 14px;
            border: none;
            border-radius: 10px;
            background: var(--accent);
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover {
            filter: brightness(0.96);
        }
        .hint {
            margin-top: 10px;
            color: var(--muted);
            font-size: 0.92rem;
        }
        .results-meta {
            margin: 10px 0 12px;
            color: var(--muted);
            font-size: 0.95rem;
        }
        .results-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 14px;
        }
        .summary-pill {
            display: inline-block;
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 6px 11px;
            color: #475569;
            font-size: 0.88rem;
            text-decoration: none;
        }
        .summary-pill:hover {
            border-color: var(--accent);
            color: var(--accent);
        }
        .summary-pill.active {
            background: var(--accent-soft);
            color: var(--accent);
            border-color: #93c5fd;
        }
        .group-section {
            margin-bottom: 18px;
        }
        .group-toggle {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 14px;
            cursor: pointer;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text);
            list-style: none;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .group-toggle::-webkit-details-marker {
            display: none;
        }
        .group-toggle::before {
            content: "▸";
            display: inline-block;
            margin-right: 8px;
            transition: transform 0.15s ease;
        }
        details[open] > .group-toggle::before {
            transform: rotate(90deg);
        }
        .group-body {
            padding-top: 10px;
        }
        .result-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .result-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 8px;
        }
        .result-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .result-link {
            display: inline-block;
            text-decoration: none;
            background: #eef2f7;
            color: #1f2937;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 7px 10px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .result-link:hover {
            background: #e2e8f0;
        }
        .result-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 0;
        }
        .result-number {
            color: var(--muted);
            font-weight: 600;
            margin-right: 6px;
        }
        .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }
        .badge {
            display: inline-block;
            background: var(--accent-soft);
            color: var(--accent);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .badge-muted {
            background: #eef2f7;
            color: #475569;
        }
        .path {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 0.84rem;
            color: var(--muted);
            word-break: break-word;
            margin-bottom: 10px;
        }
        details.source-location { margin-top: 8px; }
        details.source-location summary {
            cursor: pointer;
            color: var(--muted);
            font-size: 0.84rem;
        }
        .snippet {
            line-height: 1.55;
            white-space: pre-wrap;
        }
        mark {
            background: #fff3a3;
            color: inherit;
            padding: 0 2px;
            border-radius: 3px;
        }
        .empty-state {
            background: var(--panel);
            border: 1px dashed var(--line);
            border-radius: 12px;
            padding: 24px;
            color: var(--muted);
        }
        .quick-start {
            margin-top: 12px;
            color: var(--text);
            line-height: 1.6;
        }
        .quick-start strong {
            color: var(--accent);
        }
        .quick-start code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            background: #eef2f7;
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 0.95em;
        }
        .example-links {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }
        .example-link {
            display: inline-block;
            border: 1px solid var(--line);
            background: #fff;
            color: var(--accent);
            text-decoration: none;
            border-radius: 999px;
            padding: 7px 11px;
            font-weight: 600;
        }
        .page { max-width: 1180px; padding: clamp(12px, 3vw, 36px); }
        .search-row { grid-template-columns: minmax(260px,1fr) repeat(3,auto); }
        .search-row > div:nth-child(2) { grid-column: 1 / -1; grid-row: 2; }
        .source-filter-grid { display: flex; flex-wrap: wrap; gap: 8px 18px; }
        .result-title { font-size: 1.22rem; line-height: 1.4; overflow-wrap: anywhere; }
        .snippet { font: 1.1rem/1.65 Georgia, serif; max-width: 76ch; }
        .group-toggle { padding-block: 14px; }
        .sort-control { display: flex; gap: 8px; align-items: center; margin-top: 12px; }
        .sort-control select { width: auto; }
        :focus-visible { outline: 3px solid #2563eb; outline-offset: 2px; }
        @media (max-width: 980px) {
            .search-row {
                grid-template-columns: 1fr;
            }
            .source-filter-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="header">
            <h1>Bible Study Aid</h1><a href="/saved">Saved passages</a>
            <p>Search your local library by passage, phrase, or Bible-study topic.</p>
        </div>

        <form class="search-panel" method="get" action="/">
            <div class="search-row">
                <div>
                    <label class="field-label" for="q">Search</label>
                    <input type="text" id="q" name="q" value="{{ query }}" placeholder="Examples: Romans 8, 7 feasts of Israel, Ussher chronology" autofocus>
                </div>
                <div>
                    <label class="field-label">Source Types</label>
                    <div class="source-filter-box">
                        <div class="source-filter-grid">
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="commentary" {% if 'commentary' in selected_source_types %}checked{% endif %}> Commentaries</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="sermon_note" {% if 'sermon_note' in selected_source_types %}checked{% endif %}> Sermon Notes</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="church_sermon" {% if 'church_sermon' in selected_source_types %}checked{% endif %}> Church Sermons</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="podcast" {% if 'podcast' in selected_source_types %}checked{% endif %}> Podcasts</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="blog" {% if 'blog' in selected_source_types %}checked{% endif %}> Blogs</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="lfbi" {% if 'lfbi' in selected_source_types %}checked{% endif %}> LFBI</label>
                        </div>
                    </div>
                </div>
                <div>
                    <label class="field-label" for="mode">Match</label>
                    <select id="mode" name="mode">
                        <option value="balanced" {% if search_mode == 'balanced' %}selected{% endif %}>Best matches</option>
                        <option value="all" {% if search_mode == 'all' %}selected{% endif %}>All words</option>
                        <option value="exact" {% if search_mode == 'exact' %}selected{% endif %}>Exact phrase</option>
                    </select>
                </div>
                <div>
                    <label class="field-label" for="limit">Results</label>
                    <select id="limit" name="limit">
                        {% for option in [10, 20, 30, 50] %}
                        <option value="{{ option }}" {% if limit == option %}selected{% endif %}>{{ option }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div style="align-self: end;">
                    <button type="submit">Search</button>
                </div>
            </div>
            <label class="sort-control">Result order
                <select name="sort"><option value="rank">Best match by source type</option>
                <option value="title" {% if sort == 'title' %}selected{% endif %}>Title A–Z by source type</option>
                <option value="library" {% if sort == 'library' %}selected{% endif %}>Best matches across the library</option></select>
            </label>
            <label class="sort-control">Related wording
                <select name="related"><option value="on">Include related wording</option>
                <option value="off" {% if related == 'off' %}selected{% endif %}>Use my wording</option></select>
            </label>
            {% if searched %}
            {% for field, label, choices, current in [('book','Cited Bible book',books,book),('course','LFBI course',courses,course)] %}
            <label class="sort-control">{{ label }} <select name="{{ field }}"><option value="">All</option>
            {% if current and current not in dict(choices) %}<option selected value="{{ current }}">{{ current }} (0)</option>{% endif %}
            {% for value, count in choices %}<option value="{{ value }}" {% if current == value %}selected{% endif %}>{{ value.replace('_',' ') }} ({{ count }})</option>{% endfor %}
            </select></label>{% endfor %}
            <small>Counts show sources among the ranked matches. Choose Search to apply.</small>
            {% endif %}
            <div class="hint"><strong>Best matches</strong> is broad and ranked. Use <strong>All words</strong> to narrow a topic, or <strong>Exact phrase</strong> when wording matters.</div>
        </form>

        {% if searched %}
            <div class="results-meta">Showing {{ results|length }} {{ 'result' if results|length == 1 else 'results' }}{% if query %} for <strong>{{ query }}</strong>{% endif %}{% if selected_source_labels %} in <strong>{{ selected_source_labels | join(', ') }}</strong>{% endif %}.</div>
            <div class="results-summary">
                {% if selected_source_types %}<a class="summary-pill" href="{{ url_for('index', q=query, mode=search_mode, limit=limit, sort=sort, related=related, book=book, course=course) }}">All sources</a>{% endif %}
                {% for group in grouped_results %}<a class="summary-pill {% if selected_source_types == [group['key']] %}active{% endif %}" href="{{ url_for('index', q=query, source_types=group['key'], mode=search_mode, limit=limit, sort=sort, related=related, book=book, course=course) }}">{{ group['label'] }}: {{ group['count'] }}</a>{% endfor %}
            </div>

            {% if grouped_results %}
                {% for group in display_groups %}
                <details class="group-section" open>
                    <summary class="group-toggle">{{ group['label'] }} ({{ group['count'] }})</summary>
                    <div class="group-body">
                    {% for item in group['items'] %}
                    <div class="result-card">
                        <div class="result-top">
                            <div>
                                <div class="result-title">{{ item.highlighted_title | safe }}</div>
                                <div class="badges">
                                    {% if sort == "library" %}<span class="badge">{{ source_label(item.source_type) }}</span>{% endif %}
                                    <span class="badge">{{ item.format }}</span>
                                    {% if item.context %}<span class="badge badge-muted">{{ item.context }}</span>{% endif %}
                                </div>
                            </div>
                        </div>
                        {% for passage in item.passages %}
                        {% if loop.index == 2 %}<details><summary>Show {{ loop.length - 1 }} more {{ 'passage' if loop.length == 2 else 'passages' }}</summary>{% endif %}
                        {% if passage.evidence %}<small>{{ passage.evidence }}</small>{% endif %}
                        <div class="snippet">{{ passage.snippet | safe }}</div>
                        <a class="result-link" href="{{ url_for('open_source', path=item.path, chunk=passage.chunk_id, q=query, source_types=selected_source_types, mode=search_mode, limit=limit, sort=sort, related=related, book=book, course=course) }}">Read this passage</a>
                        <form method="post" action="/saved" style="display:inline">
                        <input type="hidden" name="path" value="{{ item.path }}"><input type="hidden" name="chunk" value="{{ passage.chunk_id }}">
                        <input type="hidden" name="q" value="{{ query }}"><input type="hidden" name="related" value="{{ related }}">
                        <input type="hidden" name="mode" value="{{ search_mode }}"><button>Save passage</button></form>
                        {% if passage.copies %}<details><summary>View other copies ({{ passage.copies|length }})</summary>
                        {% for title,path,chunk in passage.copies %}<p><a href="{{ url_for('open_source', path=path, chunk=chunk, q=query, mode=search_mode, source_types=selected_source_types, sort=sort, limit=limit, related=related, book=book, course=course) }}">{{ title }}</a></p>{% endfor %}
                        </details>{% endif %}
                        {% if loop.last and loop.length > 1 %}</details>{% endif %}
                        {% endfor %}
                        <div class="result-actions">
                            <a class="result-link" href="/reveal?path={{ item.path | urlencode }}&q={{ query | urlencode }}{% for st in selected_source_types %}&source_types={{ st | urlencode }}{% endfor %}&mode={{ search_mode | urlencode }}&limit={{ limit }}&amp;sort={{ sort }}&amp;book={{ book|urlencode }}&amp;course={{ course|urlencode }}&amp;related={{ related }}">Show in Finder</a>
                        </div>
                        <details class="source-location"><summary>File location</summary><div class="path">{{ item.path }}</div></details>
                    </div>
                    {% endfor %}
                    </div>
                </details>
                {% endfor %}
            {% else %}
                <div class="empty-state">No results found. Try broadening the query, removing a filter, or using a Scripture reference like <strong>Romans 8</strong>.</div>
            {% endif %}
        {% else %}
            <div class="empty-state">
                <div><strong>Welcome.</strong> Start with a search such as <strong>Romans 8</strong>, <strong>7 feasts of Israel</strong>, or <strong>6,000 years and 1,000 years of rest</strong>.</div>
                <div class="example-links">
                    <a class="example-link" href="/?q=Romans+8">Romans 8</a>
                    <a class="example-link" href="/?q=7+feasts+of+Israel">Seven feasts of Israel</a>
                    <a class="example-link" href="/?q=spiritual+leadership">Spiritual leadership</a>
                    <a class="example-link" href="/?q=premillennial+rapture">Premillennial rapture</a>
                </div>

            </div>
        {% endif %}
    </div>
</body>
</html>
"""


def normalize_limit(raw_limit: str) -> int:
    try:
        value = int(raw_limit)
    except Exception:
        return 20
    return value if value in {10, 20, 30, 50} else 20


def normalize_search_mode(raw_mode: str) -> str:
    return raw_mode if raw_mode in {"balanced", "all", "exact"} else "balanced"




def source_type_label(source_type: str) -> str:
    labels = {
        "commentary": "Commentaries",
        "podcast": "Podcasts",
        "blog": "Blogs",
        "sermon_note": "Sermon Notes",
        "church_sermon": "Church Sermons",
        "lfbi": "LFBI",
    }
    return labels.get(source_type, source_type.replace("_", " ").title())


def normalize_selected_source_types(raw_values):
    allowed = ["commentary", "sermon_note", "church_sermon", "podcast", "blog", "lfbi"]
    cleaned = []
    for value in raw_values:
        if value in allowed and value not in cleaned:
            cleaned.append(value)
    return cleaned


def group_results(results):
    order = ["commentary", "sermon_note", "church_sermon", "podcast", "blog", "lfbi", "unknown"]
    grouped = {key: [] for key in order}
    extras = {}

    for item in results:
        source_type = item.get("source_type", "unknown")
        if source_type in grouped:
            grouped[source_type].append(item)
        else:
            extras.setdefault(source_type, []).append(item)

    final_groups = []
    for source_type in order:
        items = grouped.get(source_type, [])
        if items:
            final_groups.append({
                "key": source_type,
                "label": source_type_label(source_type),
                "count": len(items),
                "items": items,
            })

    for source_type in sorted(extras.keys()):
        final_groups.append({
            "key": source_type,
            "label": source_type_label(source_type),
            "count": len(extras[source_type]),
            "items": extras[source_type],
        })

    return final_groups


def filter_results_by_source_types(results, selected_source_types):
    if not selected_source_types:
        return results
    allowed = set(selected_source_types)
    return [item for item in results if item.get("source_type") in allowed]


def add_result_context(results):
    enriched = []
    for display_number, item in enumerate(results, start=1):
        updated = deepcopy(item)
        updated["display_number"] = display_number
        path = Path(item.get("path", ""))
        updated["format"] = path.suffix[1:].upper() or "File"
        parts = list(path.parts[:-1])
        context_parts = []

        if item.get("source_type") == "lfbi":
            if "02_LFBI" in parts:
                start = parts.index("02_LFBI") + 1
                context_parts = parts[start:start + 2]
            elif "LFBI" in parts:
                start = parts.index("LFBI") + 1
                context_parts = parts[start:start + 2]
        elif item.get("source_type") in {"podcast", "church_sermon"} and "05_Podcasts" in parts:
            start = parts.index("05_Podcasts") + 1
            context_parts = parts[start:start + 1]
        elif item.get("source_type") == "sermon_note":
            context_parts = parts[-2:]
        elif item.get("source_type") == "commentary":
            context_parts = parts[-2:]
        elif item.get("source_type") == "blog":
            context_parts = parts[-1:]

        updated["context"] = " / ".join(
            part.replace("_", " ") for part in context_parts if part
        )
        enriched.append(updated)
    return enriched


def resolve_result_path(stored_path: str) -> Path:
    raw = (stored_path or "").strip()
    if not raw:
        raise FileNotFoundError("Empty stored path")

    candidate = Path(raw)

    if candidate.is_absolute():
        candidate = candidate.resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Absolute path does not exist: {candidate}")
        return candidate

    candidate = (BASE / raw).resolve()
    try:
        candidate.relative_to(BASE.resolve())
    except ValueError:
        raise FileNotFoundError(f"Relative path escaped BASE: {raw}")
    if not candidate.exists():
        raise FileNotFoundError(f"Relative path does not exist under BASE: {candidate}")
    return candidate

def active_terms(query):
    if request.args.get("related") == "off":
        return []
    terms = qbs.get_topic_expansion_terms(query)
    if request.args.get("mode", "balanced") == "balanced":
        terms += qbs.related_phrases(query)
    return terms


def build_highlight_pattern(query: str):
    terms = qbs.focus_words(query)
    terms.extend(active_terms(query))
    query_reference = qbs.extract_query_reference(query)
    if query_reference:
        terms.append(query_reference)

    if not terms:
        return None

    unique_terms = sorted(set(terms), key=len, reverse=True)
    pattern = "|".join(re.escape(term) for term in unique_terms)
    if not pattern:
        return None

    return re.compile(rf"(?<!\w)({pattern})(?!\w)", re.IGNORECASE)


def highlight_text(text: str, pattern):
    if not pattern:
        return escape(text or "")
    pieces = pattern.split(text or "")
    return "".join(f"<mark>{escape(piece)}</mark>" if i % 2 else escape(piece)
                   for i, piece in enumerate(pieces))


def apply_highlighting(results, query: str):
    pattern = build_highlight_pattern(query)
    highlighted = []
    for item in results:
        updated = deepcopy(item)
        updated["highlighted_title"] = highlight_text(item.get("title", ""), pattern)
        updated["snippet"] = highlight_text(item.get("snippet", ""), pattern)
        for passage in updated["passages"]:
            passage["snippet"] = highlight_text(passage["snippet"], pattern)
        highlighted.append(updated)

    return highlighted

class ServerThread(threading.Thread):
    def __init__(self, flask_app, host="127.0.0.1", port=5055):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = make_server(host, port, flask_app)
        self.ctx = flask_app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def wait_for_server(url: str, timeout: float = 5.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def launch_desktop_window(url: str):
    try:
        import webview
    except Exception:
        webbrowser.open(url)
        return "browser"

    webview.create_window("Bible Study Aid", url, width=1280, height=900)
    webview.start()
    return "window"


def run_desktop_app():
    host = "127.0.0.1"
    port = 5055
    url = f"http://{host}:{port}"

    server = ServerThread(app, host=host, port=port)
    server.start()

    if not wait_for_server(url):
        server.shutdown()
        raise RuntimeError(f"Server did not start at {url}")

    try:
        launch_desktop_window(url)
    finally:
        server.shutdown()
        server.join(timeout=2)

def render_page(query, selected_source_types, search_mode, limit, results, searched):
    sort = request.args.get("sort") if request.args.get("sort") in {"library", "title"} else "rank"
    book, course = request.args.get("book", ""), request.args.get("course", "")
    results, books, courses = narrow_results(results, book, course)
    enriched_results = add_result_context(apply_highlighting(results[:limit], query))
    if sort == "title":
        enriched_results.sort(key=lambda item: (item["title"] or "").casefold())
    groups = group_results(enriched_results)
    display_groups = ([{"label": "Best matches across the library", "count": len(enriched_results),
                        "items": enriched_results}] if sort == "library" else groups)
    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        selected_source_types=selected_source_types,
        selected_source_labels=[source_type_label(x) for x in selected_source_types],
        search_mode=search_mode,
        limit=limit,
        results=enriched_results,
        sort=sort,
        books=books, courses=courses, book=book, course=course,
        related=request.args.get("related", "on"), grouped_results=groups,
        display_groups=display_groups,
        source_label=source_type_label,
        searched=searched,
    )


@app.route("/reveal", methods=["GET"])
def reveal_in_finder():
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        abort(400)
    try:
        full_path = resolve_result_path(rel_path)
    except FileNotFoundError as e:
        return f"Show in Finder failed.\nRequested path: {rel_path}\nReason: {e}\n", 404

    subprocess.run(["open", "-R", str(full_path)], check=False)

    query = request.args.get("q", "").strip()
    selected_source_types = normalize_selected_source_types(request.args.getlist("source_types"))
    search_mode = normalize_search_mode(request.args.get("mode", "balanced"))
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=100, source_types=selected_source_types, search_mode=search_mode, related=request.args.get("related") != "off")
        results = raw_results

    return render_page(query, selected_source_types, search_mode, limit, results, searched)


@app.route("/open", methods=["GET"])
def open_source():
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        abort(400)
    try:
        full_path = resolve_result_path(rel_path)
    except FileNotFoundError as e:
        return f"Open Source failed.\nRequested path: {rel_path}\nReason: {e}\n", 404

    query = request.args.get("q", "").strip()
    selected_source_types = normalize_selected_source_types(request.args.getlist("source_types"))
    search_mode = normalize_search_mode(request.args.get("mode", "balanced"))
    limit = normalize_limit(request.args.get("limit", "20"))
    return_args = [("q", query), ("mode", search_mode), ("limit", str(limit))]
    return_args.append(("sort", request.args.get("sort") if request.args.get("sort") in {"library", "title"} else "rank"))
    return_args.extend(("source_types", value) for value in selected_source_types)
    return_args.extend((k, request.args[k]) for k in ("book","course","related") if k in request.args)
    return_url = "/saved" if request.args.get("shelf") else "/?" + urlencode(return_args)

    action_args = urlencode(return_args + [("path", rel_path)])
    chunk_id = request.args.get("chunk", type=int)
    context = qbs.read_passage(rel_path, chunk_id) if chunk_id is not None else []
    if "chunk" in request.args and not context:
        abort(404, "This passage has changed. Search again to refresh the results.")
    if context:
        action_args += "&" + urlencode({"chunk": chunk_id})
    if request.args.get("native") == "1":
        if (not context and not full_path.is_relative_to(BASE.resolve())) or not full_path.is_file():
            abort(404)
    elif context or full_path.suffix.lower() in {".txt", ".md"}:
        reader_link = ""
        if full_path.is_file() and full_path.suffix.lower() in {".txt", ".md"}:
            if request.args.get("reader") == "1" or (not context and full_path.suffix.lower() == ".txt"):
                pattern = build_highlight_pattern(query)
                return render_reader(full_path, return_url, action_args, query, pattern)
            reader_link = f'<a href="/open?{escape(action_args)}&amp;reader=1">Read full transcript</a>'
        pattern = build_highlight_pattern(query)
        if context:
            sections = []
            for passage_id, text in context:
                rendered = highlight_text(text, pattern)
                if passage_id == chunk_id:
                    snippet = qbs.build_snippet(text, query, active_terms(query),
                                                qbs.extract_query_reference(query))
                    excerpt = snippet.removeprefix("...").removesuffix("...")
                    start = text.replace("\n", " ").find(excerpt)
                    if start >= 0 and excerpt:
                        end = start + len(excerpt)
                        rendered = (highlight_text(text[:start], pattern)
                                    + '<span id="selected-excerpt">'
                                    + highlight_text(text[start:end], pattern) + '</span>'
                                    + highlight_text(text[end:], pattern))
                    sections.append(f'<section id="selected-passage"><strong>Selected passage</strong><br>{rendered}</section>')
                else:
                    sections.append(rendered)
            content_html = "\n\n".join(sections)
        else:
            text = full_path.read_text(encoding="utf-8", errors="replace")
            content_html = highlight_text(text, pattern)

        save_control = ""
        if context:
            fields = {"path": rel_path, "chunk": str(chunk_id), "q": query,
                      "mode": search_mode, "related": request.args.get("related", "on")}
            inputs = "".join(f'<input type="hidden" name="{key}" value="{escape(value, quote=True)}">'
                             for key, value in fields.items())
            save_control = f'<form method="post" action="/saved">{inputs}<button>Save passage</button></form>'
        html = f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{escape(full_path.name)}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    font-size: 19px;
                    line-height: 1.7;
                    max-width: 78ch;
                    margin: 0 auto;
                    padding: 0 24px 60px;
                    background: #f7f7f7;
                    color: #111;
                }}
                .toolbar {{
                    position: sticky;
                    top: 0;
                    z-index: 10;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    align-items: center;
                    gap: 12px;
                    padding: 14px 0;
                    background: rgba(247,247,247,0.96);
                    border-bottom: 1px solid #d1d5db;
                }}
                .toolbar a, .toolbar button {{
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    background: white;
                    color: #1d4ed8;
                    padding: 8px 11px;
                    text-decoration: none;
                    font: inherit;
                    font-size: 0.9rem;
                    font-weight: 650;
                    cursor: pointer;
                }}
                mark.current {{ outline: 2px solid #774a02; background: #ffd077; }}
                .match-controls {{ display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-block: 4px; }}
                .match-controls[hidden] {{ display: none; }}
                .font-controls {{ display: flex; gap: 6px; }}
                h1 {{
                    font-size: 28px;
                    line-height: 1.25;
                    margin: 28px 0 8px;
                }}
                .location {{
                    color: #64748b;
                    font-size: 0.82rem;
                    word-break: break-word;
                    margin-bottom: 18px;
                }}
                .content {{
                    background: white;
                    padding: 28px 32px;
                    border-radius: 12px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
                    font-family: Georgia, serif;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                mark {{ background: #fff3a3; padding: 0 2px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <a href="{escape(return_url, quote=True)}">← {'Saved passages' if return_url == '/saved' else 'Back to results'}</a>
                {reader_link}
                {save_control}
                <a href="/open?{escape(action_args)}&amp;native=1">Open Source</a>
                <a href="/reveal?{escape(action_args)}">Show in Finder</a>
                <div class="font-controls">
                    <button type="button" onclick="resizeText(-1)" aria-label="Decrease text size">A−</button>
                    <button type="button" onclick="resizeText(1)" aria-label="Increase text size">A+</button>
                </div>
                <div class="match-controls" id="match-controls" hidden>
                    <button type="button" id="previous-match">Previous match</button>
                    <span id="match-count" aria-live="polite"></span>
                    <button type="button" id="next-match">Next match</button>
                </div>
            </div>
            <h1>{escape(full_path.name)}</h1>
            <div class="location">{escape(rel_path)}</div>
            <div class="content" id="source-content">{content_html}</div>
            <script>
                function resizeText(direction) {{
                    const content = document.getElementById('source-content');
                    const current = parseFloat(getComputedStyle(content).fontSize);
                    content.style.fontSize = Math.max(14, Math.min(30, current + direction)) + 'px';
                }}
                const matches = document.querySelectorAll('#source-content mark');
                const selected = document.getElementById("selected-excerpt") || document.getElementById("selected-passage");
                if (matches.length) {{
                    const previous = document.getElementById('previous-match');
                    const next = document.getElementById('next-match');
                    const count = document.getElementById('match-count');
                    document.getElementById('match-controls').hidden = false;
                    let active = 0;
                    function selectMatch(index) {{
                        matches[active].classList.remove('current');
                        active = index;
                        matches[active].classList.add('current');
                        matches[active].scrollIntoView({{block: 'center'}});
                        count.textContent = 'Match ' + (active + 1) + ' of ' + matches.length;
                        previous.disabled = active === 0;
                        next.disabled = active === matches.length - 1;
                    }}
                    previous.onclick = () => selectMatch(active - 1);
                    next.onclick = () => selectMatch(active + 1);
                    const initial = selected ? Array.from(matches).findIndex(mark => selected.contains(mark)) : 0;
                    selectMatch(Math.max(0, initial));
                    if (initial < 0) selected.scrollIntoView({{block: 'center'}});
                }} else if (selected) {{
                    selected.scrollIntoView({{block: 'center'}});
                }}
            </script>
        </body>
        </html>
        """
        return Response(html, mimetype="text/html")

    subprocess.run(["open", str(full_path)], check=False)

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=100, source_types=selected_source_types, search_mode=search_mode, related=request.args.get("related") != "off")
        results = raw_results

    return render_page(query, selected_source_types, search_mode, limit, results, searched)


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    selected_source_types = normalize_selected_source_types(request.args.getlist("source_types"))
    search_mode = normalize_search_mode(request.args.get("mode", "balanced"))
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=100, source_types=selected_source_types, search_mode=search_mode, related=request.args.get("related") != "off")
        results = raw_results

    return render_page(query, selected_source_types, search_mode, limit, results, searched)


if __name__ == "__main__":
    run_desktop_app()
