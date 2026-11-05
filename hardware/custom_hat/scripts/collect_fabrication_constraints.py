"""Archive the official manufacturing pages used for the current rule decisions."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

import requests


EVIDENCE = Path(__file__).resolve().parents[3] / "docs/references/扩展板电路仿真工具/manufacturer-rules-20261031"


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attributes):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def main():
    directory = EVIDENCE / "sources"
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, url in (("jlc-capabilities", "https://jlcpcb.com/capabilities/pcb-capabilities"),
                      ("jlc-hdi-faq", "https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq"),
                      ("kicad10-rules", "https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html")):
        row = {"name": name, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            response = requests.get(url, timeout=45)
            row["http_status"] = response.status_code
            response.raise_for_status()
            content = response.content
            (directory / (name + ".html")).write_bytes(content)
            parser = VisibleText()
            parser.feed(content.decode("utf-8", errors="replace"))
            (directory / (name + ".txt")).write_text("\n".join(parser.parts) + "\n", encoding="utf-8")
            row["sha256"] = hashlib.sha256(content).hexdigest()
            row["bytes"] = len(content)
        except requests.RequestException as error:
            row["error"] = str(error)
        rows.append(row)
    (EVIDENCE / "sources-manifest.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
