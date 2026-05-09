"""Generate a static HTML report from a report.json file.

No JS dependencies. Inline CSS for a single self-contained file.
"""

import json
from html import escape
from pathlib import Path


_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, sans-serif;
       max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fafafa; }
h1 { font-size: 1.4rem; margin-bottom: 0.3rem; }
.meta { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }
.summary { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.summary .card { background: #fff; border: 1px solid #ddd; border-radius: 6px;
                 padding: 0.75rem 1.2rem; min-width: 100px; text-align: center; }
.card .num { font-size: 1.6rem; font-weight: 700; }
.card .lbl { font-size: 0.75rem; color: #666; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ddd; border-radius: 6px; overflow: hidden; }
th { background: #f5f5f5; text-align: left; padding: 0.6rem 0.8rem; font-size: 0.8rem;
     color: #555; border-bottom: 1px solid #ddd; }
td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; font-size: 0.85rem; vertical-align: top; }
tr:last-child td { border-bottom: none; }
.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 3px;
         font-size: 0.75rem; font-weight: 600; }
.badge-unchanged { background: #e8f5e9; color: #2e7d32; }
.badge-changed { background: #fff3e0; color: #e65100; }
.sev-none { background: #f5f5f5; color: #888; }
.sev-minor { background: #fff8e1; color: #f9a825; }
.sev-major { background: #fce4ec; color: #c62828; }
.reason { color: #555; font-size: 0.8rem; }
.artifacts { font-size: 0.75rem; color: #888; }
"""


def _badge(status: str) -> str:
    cls = "badge-changed" if status == "changed" else "badge-unchanged"
    return f'<span class="badge {cls}">{escape(status)}</span>'


def _sev_badge(severity: str) -> str:
    cls = f"sev-{severity}"
    return f'<span class="badge {cls}">{escape(severity)}</span>'


def _build_html(report: dict) -> str:
    s = report["summary"]
    rows = ""
    for r in report["results"]:
        artifacts = []
        if r.get("diff_path"):
            artifacts.append(f'diff: {escape(r["diff_path"])}')
        if r.get("snapshot_current"):
            artifacts.append(f'snap: {escape(r["snapshot_current"])}')

        rows += f"""<tr>
  <td><strong>{escape(r['label'])}</strong><br><span class="artifacts">{escape(r['url'])}</span></td>
  <td>{_badge(r['status'])}</td>
  <td>{_sev_badge(r['severity'])}</td>
  <td><span class="reason">{escape(r['summary'])}</span></td>
  <td><span class="artifacts">{'<br>'.join(artifacts)}</span></td>
</tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DocsWatch - Run {escape(report['run_id'])}</title>
<style>{_CSS}</style></head>
<body>
<h1>DocsWatch</h1>
<p class="meta">Run {escape(report['run_id'])} &mdash; {escape(report['generated_at'])}</p>

<div class="summary">
  <div class="card"><div class="num">{s['total_urls']}</div><div class="lbl">Total</div></div>
  <div class="card"><div class="num">{s['changed']}</div><div class="lbl">Changed</div></div>
  <div class="card"><div class="num">{s['unchanged']}</div><div class="lbl">Unchanged</div></div>
  <div class="card"><div class="num">{s['major']}</div><div class="lbl">Major</div></div>
  <div class="card"><div class="num">{s['minor']}</div><div class="lbl">Minor</div></div>
</div>

<table>
<thead><tr><th>Page</th><th>Status</th><th>Severity</th><th>Summary</th><th>Artifacts</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body></html>"""


def generate_html_report(run_dir: Path) -> Path:
    """Read report.json from run_dir and write report.html next to it."""
    report_json = run_dir / "report.json"
    report = json.loads(report_json.read_text(encoding="utf-8"))
    html = _build_html(report)

    html_path = run_dir / "report.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path
