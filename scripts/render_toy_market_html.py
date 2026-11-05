"""Build offline HTML reading editions of the toy-market research.

Usage: python scripts/render_toy_market_html.py [--check]
Dependencies: markdown-it-py and Pillow (local raster image dimensions only).
Markdown remains the source of truth. No network requests are made.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/references/消费电子玩具市场研究"
PAGES = {
    "research": ("研究报告", "2026 滚动线索 · 商业机会", "先看国庆与近90天的实际线索，再看今年能力加持、逐款图鉴、机会、交付与持续价值。"),
    "competitors": ("竞品与案例", "30 个产品样本 · 10 个经营案例", "按产品、价格、服务生命周期和证据进行对照。"),
    "evidence": ("证据与方法", "分级证据 · 技术与产品来源", "保留来源、口径、反证、访问限制与审查记录。"),
    "product-atlas": ("产品图鉴", "41 个分析对象 · 非41款已售产品", "逐款查看产品形态、今年能力加持与证据边界；销售状态以各卡说明为准。"),
}
URL_RE = re.compile(r'https?://[^\s<>"\[\]“”‘’\u3000-\u303f\uff00-\uffef]+')

CSS = r"""
:root{--ink:#152a38;--muted:#5b6d78;--accent:#087b78;--line:#dce5e7;--paper:#fff;--bg:#f3f5f4;--nav:#112b3b}
*{box-sizing:border-box}html{scroll-padding-top:95px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.9 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}a:hover{color:#034d4b}a:focus-visible,button:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid #da9b39;outline-offset:4px}
.skip{position:fixed;left:16px;top:-70px;background:#fff;padding:8px 18px;z-index:10}.skip:focus{top:12px}
.topbar{position:sticky;top:0;z-index:5;background:var(--nav);color:#fff;border-bottom:1px solid #385260}
.top-inner{max-width:1480px;margin:auto;padding:13px 30px;display:flex;align-items:center;justify-content:space-between;gap:20px}
.brand{color:#fff;text-decoration:none;font-size:14px;font-weight:700;letter-spacing:.04em;white-space:nowrap}.brand small{font-weight:400;color:#b7d1d7;margin-left:14px;font-size:12px}
.page-nav{display:flex;gap:6px;flex-wrap:wrap}.page-nav a{padding:7px 15px;color:#d1e2e5;text-decoration:none;border-radius:6px;font-size:14px;white-space:nowrap}.page-nav a[aria-current=page]{background:#fff;color:#153c4a;font-weight:700}.page-nav a:hover{background:#244755;color:#fff}
.hero{max-width:1480px;margin:auto;padding:45px 34px 33px}.eyebrow{display:flex;gap:12px;align-items:center;color:var(--accent);font-size:12px;font-weight:750;letter-spacing:.12em}.eyebrow:before{content:"";width:27px;height:3px;background:var(--accent)}
h1{margin:13px 0 10px;font-size:clamp(26px,3vw,40px);font-weight:750;letter-spacing:-.025em;line-height:1.45}.intro{color:var(--muted);margin:0;font-size:15px}.meta{display:flex;align-items:center;flex-wrap:wrap;gap:9px;margin-top:20px}.meta span{padding:3px 11px;border:1px solid #d2dedf;border-radius:4px;background:#f9fbfa;font-size:12px;color:#49616b}.meta .scope-tag{background:#dff0ed;color:#11635f;border-color:#c5e3dc}
.layout{max-width:1480px;margin:0 auto;padding:0 30px 70px;display:grid;grid-template-columns:260px minmax(0,1fr);gap:28px;align-items:start}
.sidebar{position:sticky;top:91px;max-height:calc(100vh - 117px);overflow-y:auto;padding:3px 8px 15px 0;scrollbar-width:thin}.sidebar>details>summary{font-weight:700;font-size:14px;cursor:pointer;padding:8px 0}.toc-note{font-size:12px;color:var(--muted);margin:8px 0 14px}.toc{list-style:none;margin:0;padding:0}.toc>li{border-top:1px solid var(--line);padding:10px 0}.toc a{display:block;font-size:13px;line-height:1.7;text-decoration:none;color:#415761}.toc a:hover{color:var(--accent)}.toc>li>a{font-weight:600}.subtoc{margin:5px 0 0 8px;border-left:2px solid #dbe5e6;padding-left:12px}.subtoc summary{font-size:11px;color:#71848c;cursor:pointer}.subtoc ol{list-style:none;margin:6px 0 0;padding:0}.subtoc li{padding:4px 0}.subtoc a{font-size:12px;font-weight:400}
.side-actions{margin-top:19px;display:flex;flex-wrap:wrap;gap:8px}.button{border:1px solid #b8cbce;border-radius:5px;background:#fff;color:#264e59;padding:7px 11px;cursor:pointer;text-decoration:none;font-size:12px;line-height:1.5;font-family:inherit}.button:hover{background:#e5efee}
.reading{min-width:0;background:var(--paper);border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 28px #152a3805;padding:33px 42px 40px}
.prose{overflow-wrap:anywhere;min-width:0}.prose p{margin:0 0 18px}.prose h2{font-size:24px;line-height:1.55;font-weight:750;margin:44px 0 20px;padding-top:23px;border-top:1px solid var(--line)}.prose h3{font-size:18px;line-height:1.7;margin:29px 0 14px;font-weight:700}.prose h4{font-size:16px;margin:25px 0 10px}.prose h2:first-child{margin-top:0}.prose strong{color:#102f3f}.prose ul,.prose ol{padding-left:1.5em;margin:10px 0 22px}.prose li{margin:5px 0}.prose li>p{margin:4px 0}.prose blockquote{margin:0 0 23px;border-left:3px solid #6dafaa;padding:14px 18px;background:#f0f7f5;color:#52666e;font-size:13px;line-height:1.9}.prose blockquote p:last-child{margin-bottom:0}.prose blockquote strong{font-weight:550;color:#36525e}
.prose code{font-size:.88em;background:#f0f3f4;border:1px solid #e1e8e9;border-radius:3px;padding:1px 4px;color:#275263}.prose pre{overflow:auto;background:#122f40;color:#deeeef;border-radius:6px;padding:18px 20px;font-size:13px;line-height:1.75}.prose pre code{background:none;color:inherit;border:0;padding:0}.prose hr{border:0;border-top:1px solid var(--line);margin:30px 0}.prose a[id]{display:block;scroll-margin-top:95px}.prose h2,.prose h3,.prose h4{scroll-margin-top:95px}.prose :target{background:#fff7d8}.prose img{display:block;max-width:100%;width:auto;height:auto;max-height:420px;object-fit:contain;margin:20px auto;padding:14px;background:#f7faf9;border:1px solid var(--line);border-radius:8px}
.table-scroll{width:100%;overflow-x:auto;margin:20px 0 27px;border:1px solid #d6e2e4;border-radius:6px;scrollbar-width:thin;scrollbar-color:#8daeb2 #edf4f3}.table-scroll table{border-collapse:collapse;min-width:100%;font-size:13px;line-height:1.75}.table-scroll th,.table-scroll td{border-right:1px solid #e0e8e9;border-bottom:1px solid #e0e8e9;text-align:left;vertical-align:top;padding:12px 14px;min-width:9rem;max-width:30rem;overflow-wrap:anywhere}.table-scroll th{background:#edf5f4;color:#1b4f57;font-weight:700}.table-scroll tbody tr:nth-child(even){background:#f8faf9}.table-scroll tbody tr:hover{background:#edf7f5}.table-scroll tr:last-child td{border-bottom:0}.table-scroll th:last-child,.table-scroll td:last-child{border-right:0}
.footer{border-top:1px solid var(--line);margin-top:38px;padding-top:20px;color:#76838a;font-size:12px;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}.footer p{margin:0}.footer a{color:#526e77}
@media(min-width:1700px){.reading{padding-left:54px;padding-right:54px}}
@media(max-width:1000px){.layout{grid-template-columns:210px minmax(0,1fr);gap:18px;padding:0 20px 50px}.reading{padding:26px}.hero{padding:30px 23px}.top-inner{padding:12px 20px}.brand small{display:none}}
@media(max-width:740px){body{font-size:15px}.topbar{position:relative}.top-inner{align-items:flex-start;flex-direction:column;gap:8px;padding:13px 18px}.page-nav{width:100%;display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.page-nav a{min-width:0;text-align:center;white-space:normal;font-size:13px;padding:6px 11px}.hero{padding:25px 19px 22px}.layout{display:block;padding:0 12px 30px}.sidebar{position:static;max-height:none;padding:0 8px 18px}.sidebar>details{border:1px solid var(--line);background:#fff;border-radius:6px;padding:4px 13px}.sidebar>details>nav{max-height:250px;overflow:auto}.toc-note{margin:5px 0 8px}.side-actions{margin-top:10px}.reading{padding:23px 19px;border-radius:7px}.prose h2{font-size:21px}.prose h3{font-size:17px}.meta{gap:6px}.meta span{font-size:11px}.table-scroll th,.table-scroll td{min-width:8rem;padding:10px}.eyebrow{font-size:11px}}
@media print{@page{margin:15mm}body{background:#fff;color:#000;font-size:10pt;line-height:1.65}.topbar,.sidebar,.skip,.footer{display:none!important}.hero{padding:0 0 12px}.eyebrow{font-size:9pt}.hero h1{font-size:23pt}.meta{margin-top:9px}.layout{display:block;padding:0;margin:0;max-width:none}.reading{padding:0;border:0;box-shadow:none}.prose h2{font-size:16pt;margin-top:25px;break-after:avoid}.prose h3{font-size:12pt;break-after:avoid}.prose blockquote{font-size:9pt}.table-scroll{overflow:visible;border-radius:0}.table-scroll table{table-layout:fixed;min-width:0;width:100%;font-size:7.5pt}.table-scroll th,.table-scroll td{min-width:0;max-width:none;padding:5px;word-break:break-word}.table-scroll tr{break-inside:avoid}a{color:inherit;text-decoration:none}.prose pre{white-space:pre-wrap;background:#eee;color:#000}.prose :target{background:none}.prose img{max-width:100%;max-height:220mm;width:auto;height:auto;object-fit:contain;break-inside:avoid;page-break-inside:avoid}}
"""


class InspectHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.text: list[str] = []
        self.table_count = 0
        self.remote_assets: list[str] = []
        self.image_sources: list[str] = []

    def handle_starttag(self, tag, attrs):
        # Browsers use the first occurrence of duplicate HTML attributes.
        attrs = dict(reversed(attrs))
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.hrefs.append(attrs["href"])
        if tag == "table":
            self.table_count += 1
        if tag == "img":
            self.image_sources.append(attrs.get("src") or "")
        asset_attrs = {
            "script": ("src",), "img": ("src",), "iframe": ("src",),
            "link": ("href",), "base": ("href",), "source": ("src",),
            "video": ("src", "poster"), "audio": ("src",), "track": ("src",),
            "embed": ("src",), "object": ("data",), "input": ("src",),
        }
        urls = [attrs.get(attr) or "" for attr in asset_attrs.get(tag, ())]
        if tag in {"img", "source"} and attrs.get("srcset"):
            urls.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        for url in urls:
            try:
                parsed = urlsplit(url.replace("\\", "/"))
                remote = parsed.scheme or parsed.netloc
            except ValueError:
                remote = True
            if remote:
                self.remote_assets.append(url)

    def handle_data(self, data):
        self.text.append(data)


def local_image_path(src):
    """Resolve an actual HTML src without reading outside the report's media tree."""
    assert src and not any(ord(char) < 32 for char in src), f"Invalid image src: {src!r}"
    try:
        url = urlsplit(src)
    except ValueError as exc:
        raise AssertionError(f"Invalid image src: {src!r}") from exc
    assert not url.scheme and not url.netloc, f"Remote image src: {src}"
    path = unquote(url.path)
    assert path and not path.startswith("/") and "\\" not in path and ":" not in path, f"Invalid local image src: {src}"
    assert not any(ord(char) < 32 for char in path), f"Invalid local image src: {src!r}"
    media = REPORT.resolve() / "media"
    target = (REPORT / path).resolve()
    assert target.is_relative_to(media), f"Image outside media: {src}"
    assert target.is_file(), f"Missing image or not a file: {src}"
    return target


def prepare_image(token):
    # Invalid/missing sources stay visible in the markup; validate() reports them.
    src = token.attrGet("src") or ""
    token.attrSet("loading", "lazy")
    token.attrSet("decoding", "async")
    try:
        path = local_image_path(src)
    except AssertionError:
        return
    try:
        with Image.open(path) as image:
            width, height = image.size
    except OSError:
        # Keep local formats Pillow cannot inspect (e.g. SVG) without inventing dimensions.
        return
    token.attrSet("width", str(width))
    token.attrSet("height", str(height))


def visible_text(markup):
    parsed = InspectHTML()
    parsed.feed(markup)
    return re.sub(r"\s+", "", "".join(parsed.text))


def rewrite_link(url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return url
    path = parsed.path
    if path.removeprefix("./") in {f"{key}.md" for key in PAGES}:
        path = path[:-3] + ".html"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def linkify_plain_urls(children):
    result = []
    depth = 0
    for child in children:
        if child.type == "link_open":
            depth += 1
        if child.type == "link_close":
            depth -= 1
        if child.type != "text" or depth:
            result.append(child)
            continue
        start = 0
        for match in URL_RE.finditer(child.content):
            url = match.group().rstrip(".,;:!?")
            while url.endswith(")") and url.count(")") > url.count("("):
                url = url[:-1]
            before = Token("text", "", 0)
            before.content = child.content[start:match.start()]
            result.append(before)
            opening = Token("link_open", "a", 1)
            opening.attrSet("href", url)
            label = Token("text", "", 0)
            label.content = url
            result.extend([opening, label, Token("link_close", "a", -1)])
            start = match.start() + len(url)
        tail = Token("text", "", 0)
        tail.content = child.content[start:]
        result.append(tail)
    return result


def make_toc(groups):
    entries = []
    for entry in groups:
        label = html.escape(entry["label"])
        sub = ""
        if entry["children"]:
            sublinks = "".join(
                f'<li><a href="#{target}">{html.escape(text)}</a></li>'
                for target, text in entry["children"]
            )
            sub = f'<details class="subtoc"><summary>展开细目 · {len(entry["children"])}</summary><ol>{sublinks}</ol></details>'
        entries.append(f'<li><a href="#{entry["id"]}">{label}</a>{sub}</li>')
    return '<ol class="toc">' + "".join(entries) + "</ol>"


def render_page(key):
    source = (REPORT / f"{key}.md").read_text(encoding="utf-8-sig")
    md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    tokens = md.parse(source)
    assert tokens[0].type == "heading_open" and tokens[0].tag == "h1"
    title = tokens[1].content
    tokens = tokens[3:]
    original_body = md.renderer.render(tokens, md.options, {})
    groups = []
    used_ids = set(re.findall(r'<a\s+id="([^"]+)"', source))
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            anchor = f"doc-section-{index}"
            assert anchor not in used_ids
            token.attrSet("id", anchor)
            label = tokens[index + 1].content
            if token.tag == "h2":
                groups.append({"id": anchor, "label": label, "children": []})
            elif token.tag == "h3" and groups:
                groups[-1]["children"].append((anchor, label))
        if token.type == "inline" and token.children:
            token.children = linkify_plain_urls(token.children)
            for child in token.children:
                if child.type == "image":
                    prepare_image(child)
                if child.type == "link_open":
                    url = rewrite_link(child.attrGet("href") or "")
                    child.attrSet("href", url)
                    parsed_url = urlsplit(url)
                    if parsed_url.scheme in {"http", "https"} or parsed_url.netloc:
                        child.attrSet("target", "_blank")
                        child.attrSet("rel", "noopener noreferrer")
    body = md.renderer.render(tokens, md.options, {})
    body = body.replace("<table>", '<div class="table-scroll" tabindex="0" role="region" aria-label="数据表格，可横向滚动"><table>').replace("</table>", "</table></div>")
    assert visible_text(original_body) == visible_text(body), f"Text changed: {key}"
    nav = "".join(
        f'<a href="{name}.html"' + (' aria-current="page"' if name == key else "") + f'>{html.escape(data[0])}</a>'
        for name, data in PAGES.items()
    )
    label, descriptor, intro = PAGES[key]
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="全球消费电子玩具市场研究：电子化潮玩、机器人玩具与AI玩具。{html.escape(descriptor)}。信息截至2026年10月10日。">
<title>{html.escape(label)} · 全球消费电子玩具市场研究</title>
<style>{CSS}</style>
</head>
<body id="top">
<!-- Generated by scripts/render_toy_market_html.py; normalized UTF-8/LF source SHA-256: {digest} -->
<a class="skip" href="#article">跳至正文</a>
<header class="topbar"><div class="top-inner"><a class="brand" href="research.html">消费电子玩具研究<small>MARKET RESEARCH / 2026</small></a><nav class="page-nav" aria-label="报告切换">{nav}</nav></div></header>
<section class="hero" aria-label="报告概况">
<div class="eyebrow">RESEARCH BRIEF / 2026</div>
<h1>{html.escape(title)}</h1><p class="intro">{html.escape(intro)}</p>
<div class="meta"><span class="scope-tag">{html.escape(descriptor)}</span><span>信息截至 2026.10.10</span><span>公开资料 · 行业中立视角</span><span>离线阅读版</span></div>
</section>
<div class="layout">
<aside class="sidebar"><details open><summary>本页目录</summary><p class="toc-note">点击章节跳转；细目可展开。<br>浏览器查找：Ctrl / ⌘ + F</p><nav aria-label="本页章节">{make_toc(groups)}</nav></details><div class="side-actions"><button class="button" id="print-page" type="button">打印 / 保存 PDF</button><a class="button" href="{key}.md">Markdown 源文件</a></div></aside>
<main class="reading" id="article"><article class="prose">{body}</article><footer class="footer"><p>消费电子玩具市场研究 · 2026年10月10日<br>保留数据口径、来源等级及研究限制；不构成产品上市或投资承诺。</p><a href="#top">返回顶部 ↑</a></footer></main>
</div>
<script>
document.getElementById('print-page').addEventListener('click', function () {{ window.print(); }});
const mobileQuery = window.matchMedia('(max-width: 740px)');
const contents = document.querySelector('.sidebar > details');
contents.open = !mobileQuery.matches;
mobileQuery.addEventListener('change', function (event) {{ contents.open = !event.matches; }});
</script>
</body>
</html>
'''


def validate(pages):
    parsed = {}
    for name, markup in pages.items():
        doc = InspectHTML()
        doc.feed(markup)
        duplicates = [key for key, count in Counter(doc.ids).items() if count > 1]
        assert not duplicates, f"Duplicate IDs in {name}: {duplicates}"
        assert not doc.remote_assets, f"Remote assets in {name}: {doc.remote_assets}"
        for src in doc.image_sources:
            try:
                local_image_path(src)
            except AssertionError as exc:
                raise AssertionError(f"{name}: {exc}") from exc
        assert "\ufffd" not in markup, f"Encoding replacement in {name}"
        parsed[name] = doc
    checked = 0
    generated_paths = {(REPORT / name).resolve() for name in pages}
    for name, doc in parsed.items():
        for href in doc.hrefs:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            target = (REPORT / unquote(url.path)).resolve() if url.path else REPORT / name
            assert target.exists() or target in generated_paths, f"Missing file: {name} -> {href}"
            if target in generated_paths and url.fragment:
                assert unquote(url.fragment) in parsed[target.name].ids, f"Missing anchor: {name} -> {href}"
            checked += 1
    return checked, sum(doc.table_count for doc in parsed.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify content, links, and generated files without writing.")
    args = parser.parse_args()
    pages = {f"{key}.html": render_page(key) for key in PAGES}
    links, tables = validate(pages)
    for name, markup in pages.items():
        path = REPORT / name
        if args.check:
            assert path.exists(), f"Missing HTML: {path}"
            assert path.read_text(encoding="utf-8") == markup, f"Stale HTML: {path}"
        else:
            path.write_text(markup, encoding="utf-8", newline="\n")
        print(f"{'CHECK' if args.check else 'BUILD'} {name}: {len(markup.encode('utf-8')):,} bytes")
    print(f"PASS: {len(pages)} pages; {links} local links; {tables} tables; source text preserved; no remote assets.")


if __name__ == "__main__":
    main()