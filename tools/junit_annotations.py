"""Fehlschläge eines JUnit-Berichts von pytest als GitHub-Annotationen ausgeben (nur CI).

Aufruf: ``python tools/junit_annotations.py pytest.xml``. Annotationen lassen sich über die
GitHub-API lesen, ohne das Log herunterzuladen.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


def main(path: str) -> int:
    root = ET.parse(path).getroot()
    count = 0
    for case in root.iter("testcase"):
        for tag in ("failure", "error"):
            node = case.find(tag)
            if node is None:
                continue
            name = f"{case.get('classname')}.{case.get('name')}"
            detail = (node.get("message") or "") + "\n" + (node.text or "")
            title = escape(name).replace(",", "_").replace(":", "_")[:200]
            print(f"::error title={title}::{escape(detail[-3000:])}")
            count += 1
    print(f"{count} Fehlschläge")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
