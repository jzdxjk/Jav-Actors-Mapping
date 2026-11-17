"""
Convert actor-mapping.xml to actor_mapping.json.

Usage: python scripts/xml_to_json.py actor-mapping.xml actor_mapping.json

Reads formatted XML, extracts each <a> element's attributes,
splits keyword by comma into an array, and writes JSON.
Skips entries missing both zh_cn and keyword (empty entries).
"""

import json
import re
import sys


def parse_xml_line(line):
    """Parse a single <a ... /> line and return attributes dict or None."""
    m = re.search(r'zh_cn="([^"]*)"', line)
    if not m:
        return None
    zh_cn = m.group(1)

    m = re.search(r'zh_tw="([^"]*)"', line)
    zh_tw = m.group(1) if m else zh_cn

    m = re.search(r'jp="([^"]*)"', line)
    jp = m.group(1) if m else zh_cn

    m = re.search(r'keyword="([^"]*)"', line)
    keyword_raw = m.group(1) if m else ''

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

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    entries = []
    skipped_empty = 0
    skipped_no_c = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('<a '):
                continue
            entry = parse_xml_line(line)
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
        print(f"  Skipped {skipped_no_c} lines without zh_cn")
    if skipped_empty:
        print(f"  Skipped {skipped_empty} empty entries")


if __name__ == '__main__':
    main()
