"""Generate the legacy name-and-alias XML from the full actor mapping."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output paths must be different")

    root = ET.parse(args.input).getroot()
    actor = root if root.tag == "actor" else root.find("actor")
    if actor is None:
        parser.error("Input XML must contain an actor element")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<actor>"]
    for entry in actor:
        if entry.tag != "a":
            continue
        attributes = []
        for field in ("zh_cn", "zh_tw", "jp", "keyword"):
            if field in entry.attrib:
                value = escape(entry.attrib[field], {'"': "&quot;"})
                attributes.append(f'{field}="{value}"')
        lines.append(f"  <a {' '.join(attributes)} />")
    lines.append("</actor>")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
