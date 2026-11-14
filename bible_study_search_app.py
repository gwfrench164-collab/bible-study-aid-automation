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

app = Flask(__name__)

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
            <h1>Bible Study Aid</h1>
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
            <label class="sort-control">Order within each group
                <select name="sort"><option value="rank">Best match first</option>
                <option value="title" {% if sort == 'title' %}selected{% endif %}>Title A–Z</option></select>
            </label>
            <div class="hint"><strong>Best matches</strong> is broad and ranked. Use <strong>All words</strong> to narrow a topic, or <strong>Exact phrase</strong> when wording matters.</div>
        </form>

        {% if searched %}
            <div class="results-meta">Showing {{ results|length }} {{ 'result' if results|length == 1 else 'results' }}{% if query %} for <strong>{{ query }}</strong>{% endif %}{% if selected_source_labels %} in <strong>{{ selected_source_labels | join(', ') }}</strong>{% endif %}.</div>
            {% if grouped_results %}
            <div class="results-summary">
                {% if selected_source_types %}<a class="summary-pill" href="{{ url_for('index', q=query, mode=search_mode, limit=limit, sort=sort) }}">All sources</a>{% endif %}
                {% for group in grouped_results %}<a class="summary-pill {% if selected_source_types == [group['key']] %}active{% endif %}" href="{{ url_for('index', q=query, source_types=group['key'], mode=search_mode, limit=limit, sort=sort) }}">{{ group['label'] }}: {{ group['count'] }}</a>{% endfor %}
            </div>
            {% endif %}

            {% if grouped_results %}
                {% for group in grouped_results %}
                <details class="group-section" open>
                    <summary class="group-toggle">{{ group['label'] }} ({{ group['count'] }})</summary>
                    <div class="group-body">
                    {% for item in group['items'] %}
                    <div class="result-card">
                        <div class="result-top">
                            <div>
                                <div class="result-title">{{ item.highlighted_title | safe }}</div>
                                <div class="badges">
                                    <span class="badge">{{ item.format }}</span>
                                    {% if item.context %}<span class="badge badge-muted">{{ item.context }}</span>{% endif %}
                                </div>
                            </div>
                        </div>
                        <div class="snippet">{{ item.snippet | safe }}</div>
                        <div class="result-actions">
                            <a class="result-link" href="/open?path={{ item.path | urlencode }}&q={{ query | urlencode }}{% for st in selected_source_types %}&source_types={{ st | urlencode }}{% endfor %}&mode={{ search_mode | urlencode }}&limit={{ limit }}&amp;sort={{ sort }}">{{ 'Preview text' if item.format in ['TXT', 'MD'] else 'Open Source' }}</a>
                            <a class="result-link" href="/reveal?path={{ item.path | urlencode }}&q={{ query | urlencode }}{% for st in selected_source_types %}&source_types={{ st | urlencode }}{% endfor %}&mode={{ search_mode | urlencode }}&limit={{ limit }}&amp;sort={{ sort }}">Show in Finder</a>
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
                <div class="quick-start">
                    <div><strong>Quick start:</strong></div>
                    <div>1. Type a Bible reference, topic, phrase, author, or book title in the search box.</div>
                    <div>2. Click <strong>Search</strong>.</div>
                    <div>3. Use <strong>Source Types</strong> to narrow results to commentaries, church sermons, podcasts, blogs, sermon notes, or LFBI.</div>
                    <div>4. Increase <strong>Results</strong> if you want a broader survey.</div>
                    <div>5. Use <strong>Open Source</strong> to open a result and <strong>Show in Finder</strong> to jump to its location.</div>
                    <div>6. This app searches a growing local library, so results will improve as more sources are added over time.</div>
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

def build_highlight_pattern(query: str):
    terms = []
    for raw_term in re.split(r"\s+", query or ""):
        term = raw_term.strip()
        if len(term) >= 2:
            terms.append(term)

    terms.extend(qbs.get_topic_expansion_terms(query))
    query_reference = qbs.extract_query_reference(query)
    if query_reference:
        terms.append(query_reference)

    if not terms:
        return None

    unique_terms = sorted(set(terms), key=len, reverse=True)
    pattern = "|".join(re.escape(term) for term in unique_terms)
    if not pattern:
        return None

    return re.compile(f"({pattern})", re.IGNORECASE)


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
    sort = "title" if request.args.get("sort") == "title" else "rank"
    enriched_results = add_result_context(results)
    if sort == "title":
        enriched_results.sort(key=lambda item: (item["title"] or "").casefold())
    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        selected_source_types=selected_source_types,
        selected_source_labels=[source_type_label(x) for x in selected_source_types],
        search_mode=search_mode,
        limit=limit,
        results=enriched_results,
        sort=sort,
        grouped_results=group_results(enriched_results),
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
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30), source_types=selected_source_types, search_mode=search_mode)
        results = apply_highlighting(raw_results[:limit], query)

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
    return_args.append(("sort", "title" if request.args.get("sort") == "title" else "rank"))
    return_args.extend(("source_types", value) for value in selected_source_types)
    return_url = "/?" + urlencode(return_args)

    action_args = urlencode(return_args + [("path", rel_path)])
    if request.args.get("native") == "1":
        if not full_path.is_relative_to(BASE.resolve()) or not full_path.is_file():
            abort(404)
    elif full_path.suffix.lower() in {".txt", ".md"}:
        try:
            text = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = full_path.read_text(errors="ignore")

        content_html = highlight_text(text, build_highlight_pattern(query))

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
                <a href="{escape(return_url, quote=True)}">← Back to results</a>
                <a href="/open?{escape(action_args)}&amp;native=1">Open Source</a>
                <a href="/reveal?{escape(action_args)}">Show in Finder</a>
                <div class="font-controls">
                    <button type="button" onclick="resizeText(-1)" aria-label="Decrease text size">A−</button>
                    <button type="button" onclick="resizeText(1)" aria-label="Increase text size">A+</button>
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
                const firstMatch = document.querySelector('mark');
                if (firstMatch) firstMatch.scrollIntoView({{block: 'center'}});
            </script>
        </body>
        </html>
        """
        return Response(html, mimetype="text/html")

    subprocess.run(["open", str(full_path)], check=False)

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30), source_types=selected_source_types, search_mode=search_mode)
        results = apply_highlighting(raw_results[:limit], query)

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
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30), source_types=selected_source_types, search_mode=search_mode)
        results = apply_highlighting(raw_results[:limit], query)

    return render_page(query, selected_source_types, search_mode, limit, results, searched)


if __name__ == "__main__":
    run_desktop_app()
