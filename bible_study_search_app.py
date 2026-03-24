from pathlib import Path
import sys
import threading
import time
import webbrowser
import subprocess
from html import escape
from flask import Flask, request, render_template_string, abort

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
            grid-template-columns: minmax(300px, 1fr) 180px 120px 120px;
            gap: 10px;
            align-items: center;
        }
        .field-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--muted);
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
        .snippet {
            line-height: 1.55;
            white-space: pre-wrap;
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
        @media (max-width: 980px) {
            .search-row {
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
                    <label class="field-label" for="source_type">Source Type</label>
                    <select id="source_type" name="source_type">
                        <option value="all" {% if source_type == 'all' %}selected{% endif %}>All Sources</option>
                        <option value="commentary" {% if source_type == 'commentary' %}selected{% endif %}>Commentary</option>
                        <option value="podcast" {% if source_type == 'podcast' %}selected{% endif %}>Podcast</option>
                        <option value="blog" {% if source_type == 'blog' %}selected{% endif %}>Blog</option>
                        <option value="sermon_note" {% if source_type == 'sermon_note' %}selected{% endif %}>Sermon Note</option>
                        <option value="lfbi" {% if source_type == 'lfbi' %}selected{% endif %}>LFBI</option>
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
            <div class="hint">For the best results, try broad Bible-study questions, exact Scripture references, or named teachers and books.</div>
        </form>

        {% if searched %}
            <div class="results-meta">Showing {{ results|length }} result(s){% if query %} for <strong>{{ query }}</strong>{% endif %}{% if source_type != 'all' %} in <strong>{{ source_type }}</strong>{% endif %}.</div>

            {% if grouped_results %}
                {% for group in grouped_results %}
                <details class="group-section" open>
                    <summary class="group-toggle">{{ group['label'] }} ({{ group['count'] }})</summary>
                    <div class="group-body">
                    {% for item in group['items'] %}
                    <div class="result-card">
                        <div class="result-top">
                            <div>
                                <div class="result-title">{{ item.title }}</div>
                                <div class="badges">
                                    <span class="badge">{{ item.source_type }}</span>
                                    <span class="badge badge-muted">score {{ item.score }}</span>
                                </div>
                            </div>
                        </div>
                        <div class="path">{{ item.path }}</div>
                        <div class="snippet">{{ item.snippet }}</div>
                        <div class="result-actions">
                            <a class="result-link" href="/open?path={{ item.path | urlencode }}&q={{ query | urlencode }}&source_type={{ source_type | urlencode }}&limit={{ limit }}">Open Source</a>
                            <a class="result-link" href="/reveal?path={{ item.path | urlencode }}&q={{ query | urlencode }}&source_type={{ source_type | urlencode }}&limit={{ limit }}">Show in Finder</a>
                        </div>
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
                <div class="quick-start">
                    <div><strong>Quick start:</strong></div>
                    <div>1. Type a Bible reference, topic, phrase, author, or book title in the search box.</div>
                    <div>2. Click <strong>Search</strong>.</div>
                    <div>3. Use <strong>Source Type</strong> if you want to narrow results to commentaries, podcasts, blogs, sermon notes, or LFBI.</div>
                    <div>4. Increase <strong>Results</strong> if you want a broader survey.</div>
                    <div>5. Leave this window open while the app is running at <code>http://127.0.0.1:5055</code>.</div>
                    <div>6. The next quality-of-life improvement is a one-click Mac launcher so you do not need Terminal for normal use.</div>
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


def open_browser_delayed():
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:5055")


def source_type_label(source_type: str) -> str:
    labels = {
        "commentary": "Commentaries",
        "podcast": "Podcasts",
        "blog": "Blogs",
        "sermon_note": "Sermon Notes",
        "lfbi": "LFBI",
    }
    return labels.get(source_type, source_type.replace("_", " ").title())


def group_results(results):
    order = ["commentary", "sermon_note", "podcast", "blog", "lfbi", "unknown"]
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


def resolve_result_path(rel_path: str) -> Path:
    candidate = (BASE / rel_path).resolve()
    try:
        candidate.relative_to(BASE.resolve())
    except ValueError:
        raise FileNotFoundError(rel_path)
    if not candidate.exists():
        raise FileNotFoundError(rel_path)
    return candidate


@app.route("/reveal", methods=["GET"])
def reveal_in_finder():
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        abort(400)
    try:
        full_path = resolve_result_path(rel_path)
    except FileNotFoundError:
        abort(404)

    subprocess.run(["open", "-R", str(full_path)], check=False)

    query = request.args.get("q", "").strip()
    source_type = request.args.get("source_type", "all").strip() or "all"
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        if source_type != "all":
            raw_results = [item for item in raw_results if item.get("source_type") == source_type]
        results = raw_results[:limit]

    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        source_type=source_type,
        limit=limit,
        results=results,
        grouped_results=group_results(results),
        searched=searched,
    )


@app.route("/open", methods=["GET"])
def open_source():
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        abort(400)
    try:
        full_path = resolve_result_path(rel_path)
    except FileNotFoundError:
        abort(404)

    subprocess.run(["open", str(full_path)], check=False)

    query = request.args.get("q", "").strip()
    source_type = request.args.get("source_type", "all").strip() or "all"
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        if source_type != "all":
            raw_results = [item for item in raw_results if item.get("source_type") == source_type]
        results = raw_results[:limit]

    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        source_type=source_type,
        limit=limit,
        results=results,
        grouped_results=group_results(results),
        searched=searched,
    )


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    source_type = request.args.get("source_type", "all").strip() or "all"
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        if source_type != "all":
            raw_results = [item for item in raw_results if item.get("source_type") == source_type]
        results = raw_results[:limit]

    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        source_type=source_type,
        limit=limit,
        results=results,
        grouped_results=group_results(results),
        searched=searched,
    )


if __name__ == "__main__":
    threading.Thread(target=open_browser_delayed, daemon=True).start()
    app.run(host="127.0.0.1", port=5055, debug=False)