"""
Convert actor-mapping.xml to actor_mapping.json.

Usage: python xml_to_json.py actor-mapping.xml actor_mapping.json

Reads XML, extracts each <a> element's attributes,
splits keyword by comma into an array, and writes JSON.
Skips entries missing both zh_cn and keyword (empty entries).
"""

import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def parse_xml_line(line):
    """Parse a single XML element using the same rules as the full converter."""
    return parse_xml_entry(ET.fromstring(line))


def parse_xml_entry(entry):
    """Project decoded XML attributes into the existing JSON representation."""
    if "zh_cn" not in entry.attrib:
        return None
    zh_cn = entry.get("zh_cn")
    zh_tw = entry.get("zh_tw", zh_cn)
    jp = entry.get("jp", zh_cn)
    keyword_raw = entry.get("keyword", "")

    # Split keyword by comma (both ASCII and fullwidth)
    aliases = []
    if keyword_raw:
        for part in re.split(r'[,，]', keyword_raw):
            part = part.strip()
            if part:
                aliases.append(part)

    # Deduplicate while preserving order
    seen = set()
    unique_aliases = []
    for a in aliases:
        if a not in seen:
            seen.add(a)
            unique_aliases.append(a)

    return {"c": zh_cn, "t": zh_tw, "j": jp, "a": unique_aliases}


def main():
    if len(sys.argv) < 3:
        print("Usage: python xml_to_json.py <input.xml> <output.json>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different")

    root = ET.parse(input_path).getroot()
    actor = root if root.tag == "actor" else root.find("actor")
    if actor is None:
        raise ValueError("Input XML must contain an actor element")

    entries = []
    skipped_empty = 0
    skipped_no_c = 0

    for element in actor:
        if element.tag != "a":
            continue
        entry = parse_xml_entry(element)
        if entry is None:
            skipped_no_c += 1
            continue
        if not entry['a'] and not entry['c']:
            skipped_empty += 1
            continue
        entries.append(entry)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Converted {len(entries)} entries to {output_path}")
    if skipped_no_c:
        print(f"  Skipped {skipped_no_c} entries without zh_cn")
    if skipped_empty:
        print(f"  Skipped {skipped_empty} empty entries")


if __name__ == '__main__':
    main()
