from pathlib import Path
import sys
import subprocess
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
            grid-template-columns: minmax(300px, 1fr) 260px 120px 120px;
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
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="podcast" {% if 'podcast' in selected_source_types %}checked{% endif %}> Podcasts</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="blog" {% if 'blog' in selected_source_types %}checked{% endif %}> Blogs</label>
                            <label class="source-filter-item"><input type="checkbox" name="source_types" value="lfbi" {% if 'lfbi' in selected_source_types %}checked{% endif %}> LFBI</label>
                        </div>
                    </div>
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
            <div class="results-meta">Showing {{ results|length }} result(s){% if query %} for <strong>{{ query }}</strong>{% endif %}{% if selected_source_labels %} in <strong>{{ selected_source_labels | join(', ') }}</strong>{% endif %}.</div>

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
                            <a class="result-link" href="/open?path={{ item.path | urlencode }}&q={{ query | urlencode }}{% for st in selected_source_types %}&source_types={{ st | urlencode }}{% endfor %}&limit={{ limit }}">Open Source</a>
                            <a class="result-link" href="/reveal?path={{ item.path | urlencode }}&q={{ query | urlencode }}{% for st in selected_source_types %}&source_types={{ st | urlencode }}{% endfor %}&limit={{ limit }}">Show in Finder</a>
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
                    <div>3. Use <strong>Source Types</strong> if you want to narrow results to one or more categories like commentaries, podcasts, blogs, sermon notes, or LFBI.</div>
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




def source_type_label(source_type: str) -> str:
    labels = {
        "commentary": "Commentaries",
        "podcast": "Podcasts",
        "blog": "Blogs",
        "sermon_note": "Sermon Notes",
        "lfbi": "LFBI",
    }
    return labels.get(source_type, source_type.replace("_", " ").title())


def normalize_selected_source_types(raw_values):
    allowed = ["commentary", "sermon_note", "podcast", "blog", "lfbi"]
    cleaned = []
    for value in raw_values:
        if value in allowed and value not in cleaned:
            cleaned.append(value)
    return cleaned


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


def filter_results_by_source_types(results, selected_source_types):
    if not selected_source_types:
        return results
    allowed = set(selected_source_types)
    return [item for item in results if item.get("source_type") in allowed]


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


def render_page(query, selected_source_types, limit, results, searched):
    return render_template_string(
        PAGE_TEMPLATE,
        query=query,
        selected_source_types=selected_source_types,
        selected_source_labels=[source_type_label(x) for x in selected_source_types],
        limit=limit,
        results=results,
        grouped_results=group_results(results),
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
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        raw_results = filter_results_by_source_types(raw_results, selected_source_types)
        results = raw_results[:limit]

    return render_page(query, selected_source_types, limit, results, searched)


@app.route("/open", methods=["GET"])
def open_source():
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        abort(400)
    try:
        full_path = resolve_result_path(rel_path)
    except FileNotFoundError as e:
        return f"Open Source failed.\nRequested path: {rel_path}\nReason: {e}\n", 404

    subprocess.run(["open", str(full_path)], check=False)

    query = request.args.get("q", "").strip()
    selected_source_types = normalize_selected_source_types(request.args.getlist("source_types"))
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        raw_results = filter_results_by_source_types(raw_results, selected_source_types)
        results = raw_results[:limit]

    return render_page(query, selected_source_types, limit, results, searched)


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    selected_source_types = normalize_selected_source_types(request.args.getlist("source_types"))
    limit = normalize_limit(request.args.get("limit", "20"))

    results = []
    searched = bool(query)

    if query:
        raw_results = qbs.run_query(query, limit=max(limit * 2, 30))
        raw_results = filter_results_by_source_types(raw_results, selected_source_types)
        results = raw_results[:limit]

    return render_page(query, selected_source_types, limit, results, searched)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=False)