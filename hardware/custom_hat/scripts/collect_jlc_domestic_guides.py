"""Archive the user-specified domestic JLC fabrication guides for local comparison."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from lxml import html


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/references/归档扩展板嘉立创规则自查"
SOURCES = {
    "before-order": "https://www.jlc.com/portal/server_guide_112.html",
    "order-operator": "https://www.jlc.com/portal/server_guide_111.html",
    "pcb-capabilities": "https://www.jlc.com/portal/vtechnology.html?active=pcb",
    "via-process": "https://www.jlc.com/portal/server_guide_15544.html",
    "stackup-guide": "https://www.jlc.com/portal/server_guide_36372.html",
    "mask-guide": "https://www.jlc.com/portal/server_guide_34402.html",
    "via-fill-rules": "https://www.jlc.com/portal/q7i38630.html",
    "smt-guide-64042": "https://www.jlc-smt.com/technology/detail/64042.html",
    "smt-capabilities": "https://www.jlc-smt.com/vtechnology",
}


def collect(entry):
    name, url = entry
    record = {"name": name, "url": url}
    try:
        path = OUTPUT / "sources" / (name + ".html")
        if path.exists():
            existing = json.loads((OUTPUT / "sources-manifest.json").read_text(encoding="utf-8"))
            record = next(item for item in existing["sources"] if item["name"] == name)
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                raise RuntimeError("Archived source no longer matches its manifest")
            return record
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as response:
            content = response.read()
            record.update(status=response.status, resolved_url=response.url)
        path.write_bytes(content)
        document = html.fromstring(content)
        for element in document.xpath("//script|//style"):
            element.drop_tree()
        lines = [text.strip() for text in document.xpath("//text()") if text.strip()]
        (path.with_suffix(".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        tables = [[" | ".join(" ".join(cell.itertext()).strip() for cell in row.xpath("./td|./th"))
                   for row in table.xpath(".//tr")] for table in document.xpath("//table")]
        (OUTPUT / "sources" / (name + "-tables.json")).write_text(json.dumps(tables, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        links = [{"text": " ".join(element.itertext()).strip(), "href": element.get("href")}
                 for element in document.xpath("//a[@href]")]
        (OUTPUT / "sources" / (name + "-links.json")).write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record.update(sha256=hashlib.sha256(content).hexdigest(), text_lines=len(lines), tables=len(tables),
                      title=" ".join(document.xpath("//title/text()")))
    except Exception as error:
        record["error"] = str(error)
    return record


def main():
    (OUTPUT / "sources").mkdir(parents=True, exist_ok=True)
    directory = OUTPUT / "sources/smt-guide-64042.html"
    if directory.exists():
        document = html.fromstring(directory.read_bytes())
        for anchor in document.xpath("//table//a[@href]"):
            url = anchor.get("href")
            if url.startswith("https://www.jlc-smt.com/technology/detail/"):
                identifier = Path(url).stem
                SOURCES["smt-rule-" + identifier] = url
    with ThreadPoolExecutor(max_workers=3) as executor:
        records = list(executor.map(collect, SOURCES.items()))
    result = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "sources": records,
              "scope": "Public documentation only; no upload, order creation, payment or factory acceptance"}
    (OUTPUT / "sources-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
