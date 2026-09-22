"""Re-fetch the MAX developer docs (dev.max.ru) into docs/max/reference as Markdown.

Usage (from repo root):
    uv run --with markdownify --with beautifulsoup4 --with pyyaml python docs/max/scripts/update_docs.py

Also refreshes docs/max/openapi (official OpenAPI schema) and
docs/max/python-maxapi (docs + examples of the `maxapi` Python library) via git clone.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

BASE = "https://dev.max.ru"
ROOT = Path(__file__).resolve().parents[1]  # docs/max
REF = ROOT / "reference"
UA = {"User-Agent": "Mozilla/5.0"}


class Converter(MarkdownConverter):
    def convert_pre(self, el, text, parent_tags=None):
        classes = el.get("class", []) + [c for x in el.find_all("code") for c in x.get("class", [])]
        m = re.search(r"language-(\w+)", " ".join(classes))
        lang = m.group(1).lower() if m else ""
        return f"\n```{lang}\n{el.get_text().rstrip()}\n```\n"


def crawl() -> dict[str, str]:
    pages, queue = {}, ["/docs", "/docs-api", "/help"]
    while queue:
        path = queue.pop(0)
        if path in pages:
            continue
        try:
            req = urllib.request.Request(BASE + path, headers=UA)
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:  # 404 links exist in the nav
            print("skip", path, e)
            pages[path] = ""
            continue
        pages[path] = html
        queue += [l for l in re.findall(r'href="(/(?:docs|help)[^"#?]*)"', html) if l not in pages]
    return {p: h for p, h in pages.items() if h}


def rsc_rows(html: str) -> dict:
    """Next.js RSC payload (self.__next_f.push) — holds content of inactive tabs."""
    pushes = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html)
    data = "".join(json.loads(p) for p in pushes).encode()
    rows, pos = {}, 0
    # Row format: "<hex id>:<json>\n" or text row "<hex id>:T<hex byte len>,<raw text>"
    while pos < len(data):
        m = re.compile(rb"([0-9a-f]+):").match(data, pos)
        if not m:
            nl = data.find(b"\n", pos)
            pos = len(data) if nl < 0 else nl + 1
            continue
        key, pos = m.group(1).decode(), m.end()
        t = re.compile(rb"T([0-9a-f]+),").match(data, pos)
        if t:
            size = int(t.group(1), 16)
            rows[key] = data[t.end():t.end() + size].decode("utf-8", "replace")
            pos = t.end() + size
            continue
        nl = data.find(b"\n", pos)
        nl = len(data) if nl < 0 else nl
        try:
            rows[key] = json.loads(data[pos:nl])
        except ValueError:
            pass
        pos = nl + 1
    return rows


def rsc_to_html(node, rows, depth=0) -> str:
    if depth > 60:
        return ""
    if isinstance(node, str):
        ref = re.fullmatch(r"\$[L@]?([0-9a-f]+)", node)  # "$1a", lazy "$L1a", promise "$@1a"
        if ref:
            return rsc_to_html(rows.get(ref.group(1)), rows, depth + 1)
        if node.startswith("$$"):  # escaped literal "$"
            return escape(node[1:])
        return "" if node.startswith("$") else escape(node)
    if isinstance(node, list):
        if len(node) == 4 and node[0] == "$" and isinstance(node[3], dict):
            tag, props = node[1], node[3]
            inner = rsc_to_html(props.get("children"), rows, depth + 1)
            if isinstance(tag, str) and re.fullmatch(r"[a-z][a-z0-9]*", tag):
                cls = props.get("className")
                attr = f' class="{escape(cls)}"' if isinstance(cls, str) else ""
                if tag == "a" and isinstance(props.get("href"), str):
                    attr += f' href="{escape(props["href"])}"'
                return f"<{tag}{attr}>{inner}</{tag}>"
            return inner
        return "".join(rsc_to_html(x, rows, depth + 1) for x in node)
    return ""


def tab_sections(html: str) -> list[tuple[str, str]]:
    rows, found = rsc_rows(html), []

    def walk(node):
        if isinstance(node, list):
            if (len(node) == 4 and node[0] == "$" and isinstance(node[3], dict)
                    and isinstance(node[3].get("title"), str) and "children" in node[3]):
                found.append((node[3]["title"], rsc_to_html(node[3]["children"], rows)))
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for x in node.values():
                walk(x)

    for row in rows.values():
        walk(row)
    return found


def to_markdown(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body
    for t in main.find_all(["svg", "button", "script", "style", "nav"]):
        t.decompose()
    # Code blocks are <div><div>header: lang + "Скопировать"</div><div><code>…</code></div></div>
    for code in main.find_all("code"):
        box = code.parent.parent if code.parent is not None else None
        is_block = (
            code.parent.name == "div" and box is not None and "Скопировать" in box.get_text()[:200]
        )
        if ("language-" in " ".join(code.get("class", [])) or is_block) and code.parent.name != "pre":
            pre = soup.new_tag("pre")
            code.extract()
            pre.append(code)
            box.replace_with(pre)
    for a in main.find_all("a", href=True):
        if a["href"].startswith("/"):
            a["href"] = BASE + a["href"]
    conv = Converter(heading_style="ATX", bullets="-")
    md = conv.convert_soup(main)
    # Inactive tabs are not in the rendered HTML — append them from the RSC payload
    extra = []
    for title, tab_html in tab_sections(html):
        tab_soup = BeautifulSoup(tab_html, "html.parser")
        for code in tab_soup.find_all("code"):
            if "language-" in " ".join(code.get("class", [])) and code.parent.name != "pre":
                pre = tab_soup.new_tag("pre")
                code.replace_with(pre)
                pre.append(code)
        for a in tab_soup.find_all("a", href=True):
            if a["href"].startswith("/"):
                a["href"] = BASE + a["href"]
        tab_md = conv.convert_soup(tab_soup).strip()
        if tab_md and tab_md not in md and all(tab_md != t for _, t in extra):
            extra.append((title, tab_md))
    if extra:
        md += "\n\n## Содержимое вкладок\n\n_На сайте эти блоки показаны вкладками; здесь — все варианты, кроме уже показанного выше._\n\n"
        md += "\n\n".join(f"### Вкладка: {t}\n\n{body}" for t, body in extra)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return f"<!-- source: {url} -->\n\n{md}\n"


def local_path(path: str) -> Path:
    if path == "/docs":
        return REF / "platform/index.md"
    if path == "/docs-api":
        return REF / "api/index.md"
    if path.startswith("/docs-api/methods/"):
        verb, *rest = path[len("/docs-api/methods/"):].split("/")
        return REF / "api/methods" / (verb + "_" + "_".join(rest).replace("-", "") + ".md")
    if path.startswith("/docs-api/"):
        return REF / "api" / (path[len("/docs-api/"):] + ".md")
    if path == "/help":
        return REF / "faq/index.md"
    if path.startswith("/help/"):
        return REF / "faq" / (path[len("/help/"):] + ".md")
    return REF / "platform" / (path[len("/docs/"):] + ".md")


def clone(repo: str, dest: Path) -> str:
    subprocess.run(["git", "clone", "-q", "--depth", "1", repo, str(dest)], check=True)
    return subprocess.run(
        ["git", "-C", str(dest), "log", "-1", "--format=%H %ci"], capture_output=True, text=True
    ).stdout


def main():
    pages = crawl()
    shutil.rmtree(REF, ignore_errors=True)
    for path, html in pages.items():
        out = local_path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_markdown(html, BASE + path))
    print(f"reference: {len(pages)} pages")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sha = clone("https://github.com/max-messenger/api-schema", tmp / "schema")
        (ROOT / "openapi").mkdir(exist_ok=True)
        for f in ("schema.yaml", "README.mdx"):
            shutil.copy(tmp / "schema" / f, ROOT / "openapi" / f)
        (ROOT / "openapi/SOURCE_COMMIT").write_text(sha)

        sha = clone("https://github.com/love-apples/maxapi", tmp / "maxapi")
        dst = ROOT / "python-maxapi"
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(tmp / "maxapi/docs", dst / "docs")
        shutil.copytree(tmp / "maxapi/examples", dst / "examples")
        shutil.copy(tmp / "maxapi/README.md", dst / "README.md")
        (dst / "SOURCE_COMMIT").write_text(sha)
    print("openapi + python-maxapi refreshed")

    from gen_schema_md import main as gen_schema  # needs pyyaml

    gen_schema()


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.path.insert(0, str(Path(__file__).parent))
    main()
