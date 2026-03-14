
from __future__ import annotations

import html
from pathlib import Path

from django.http import Http404, HttpResponse


DOCS_DIR = Path(__file__).resolve().parent.parent / 'docs'


def _wrap_document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #edf3f1;
      --card: #ffffff;
      --ink: #1d2939;
      --muted: #475467;
      --brand: #0f766e;
      --border: #d0d5dd;
      --soft: #e7f4f1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: radial-gradient(circle at top right, #dbeee8 0, var(--bg) 35%);
      color: var(--ink);
      line-height: 1.6;
    }}
    .shell {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero, .doc {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      margin-bottom: 18px;
      box-shadow: 0 18px 40px rgba(15, 118, 110, 0.08);
    }}
    .eyebrow {{
      color: var(--brand);
      text-transform: uppercase;
      letter-spacing: .08em;
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 8px;
    }}
    h1 {{ font-size: 34px; margin: 0 0 8px; }}
    h2 {{ font-size: 26px; margin-top: 28px; margin-bottom: 12px; }}
    h3 {{ font-size: 20px; margin-top: 22px; margin-bottom: 10px; }}
    h4 {{ font-size: 16px; margin-top: 18px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }}
    p {{ margin: 10px 0; }}
    ul, ol {{ margin: 10px 0 10px 22px; padding: 0; }}
    li {{ margin: 6px 0; }}
    code {{
      background: #f4f7f6;
      border: 1px solid #d8e2df;
      padding: 1px 6px;
      border-radius: 6px;
      font-family: Consolas, monospace;
      font-size: 0.95em;
    }}
    .nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .nav a {{
      display: inline-flex;
      align-items: center;
      padding: 10px 14px;
      border-radius: 999px;
      background: var(--soft);
      color: #0b4d47;
      font-weight: 700;
      text-decoration: none;
      border: 1px solid #c7e6df;
    }}
    .sub {{ color: var(--muted); margin: 0; }}
    @media print {{
      body {{ background: #ffffff; }}
      .shell {{ max-width: none; padding: 0; }}
      .hero, .doc {{ box-shadow: none; border-radius: 0; border: 0; padding: 0; margin-bottom: 20px; }}
      .nav {{ display: none; }}
      a {{ color: inherit; text-decoration: none; }}
    }}
    @media (max-width: 820px) {{
      .shell {{ padding: 16px; }}
      h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Documentation</div>
      <h1>{html.escape(title)}</h1>
      <p class="sub">Browser-friendly product documentation and buyer-facing material for Debt & Risk Intelligence Hub.</p>
      <nav class="nav">
        <a href="/docs/user-guide/">User Guide</a>
        <a href="/docs/manual-testing-guide/">Manual Testing Guide</a>
        <a href="/docs/admin-panel-guide/">Admin Panel Guide</a>
        <a href="/docs/buyer-guide/">Buyer Guide</a>
        <a href="/docs/buyer-one-pager/">Buyer One-Pager</a>
        <a href="/dashboard/">Open App</a>
      </nav>
      <nav class="nav">
        <a href="javascript:window.print()">Print / Save PDF</a>
      </nav>
    </section>
    <section class="doc">{body}</section>
  </main>
</body>
</html>"""


def _render_markdown_like(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append('</ul>')
            in_list = False

    def render_inline(text: str) -> str:
        escaped = html.escape(text)
        rendered: list[str] = []
        open_code = False
        buffer = []
        for char in escaped:
            if char == '`':
                if open_code:
                    rendered.append('<code>' + ''.join(buffer) + '</code>')
                    buffer = []
                    open_code = False
                else:
                    if buffer:
                        rendered.append(''.join(buffer))
                        buffer = []
                    open_code = True
            else:
                buffer.append(char)
        if buffer:
            rendered.append(''.join(buffer))
        return ''.join(rendered)

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        if stripped.startswith('# '):
            close_list()
            parts.append(f'<h2>{render_inline(stripped[2:])}</h2>')
        elif stripped.startswith('## '):
            close_list()
            parts.append(f'<h2>{render_inline(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            close_list()
            parts.append(f'<h3>{render_inline(stripped[4:])}</h3>')
        elif stripped.startswith('#### '):
            close_list()
            parts.append(f'<h4>{render_inline(stripped[5:])}</h4>')
        elif stripped.startswith('- '):
            if not in_list:
                parts.append('<ul>')
                in_list = True
            parts.append(f'<li>{render_inline(stripped[2:])}</li>')
        else:
            close_list()
            parts.append(f'<p>{render_inline(stripped)}</p>')
    close_list()
    return ''.join(parts)


def _serve_html_doc(filename: str, title: str) -> HttpResponse:
    path = DOCS_DIR / filename
    if not path.exists():
        raise Http404('Document not found.')
    content = path.read_text(encoding='utf-8')
    return HttpResponse(content, content_type='text/html; charset=utf-8')


def user_guide(_request):
    path = DOCS_DIR / 'user_guide.md'
    if not path.exists():
        raise Http404('User guide not found.')
    markdown_text = path.read_text(encoding='utf-8')
    body = _render_markdown_like(markdown_text)
    return HttpResponse(_wrap_document('Debt & Risk Intelligence Hub - User Guide', body), content_type='text/html; charset=utf-8')


def buyer_guide(_request):
    return _serve_html_doc('buyer_presentation_guide.html', 'Debt & Risk Intelligence Hub - Buyer Presentation Guide')


def buyer_one_pager(_request):
    return _serve_html_doc('buyer_one_pager.html', 'Debt & Risk Intelligence Hub - Buyer One-Pager')


def manual_testing_guide(_request):
    path = DOCS_DIR / 'manual_testing_guide.md'
    if not path.exists():
        raise Http404('Manual testing guide not found.')
    markdown_text = path.read_text(encoding='utf-8')
    body = _render_markdown_like(markdown_text)
    return HttpResponse(
        _wrap_document('Debt & Risk Intelligence Hub - Manual Testing Guide', body),
        content_type='text/html; charset=utf-8',
    )


def admin_panel_guide(_request):
    path = DOCS_DIR / 'admin_panel_guide.md'
    if not path.exists():
        raise Http404('Admin panel guide not found.')
    markdown_text = path.read_text(encoding='utf-8')
    body = _render_markdown_like(markdown_text)
    return HttpResponse(
        _wrap_document('Debt & Risk Intelligence Hub - Admin Panel Guide', body),
        content_type='text/html; charset=utf-8',
    )
