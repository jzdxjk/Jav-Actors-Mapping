import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
JSON_SCRIPT = ROOT / "xml_to_json.py"
XML_SCRIPT = ROOT / "scripts" / "generate_compatibility_mapping.py"


class CompatibilityMappingTests(unittest.TestCase):
    def convert(self, script, source, extension):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.xml"
            output_path = Path(directory) / f"result.{extension}"
            source_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(source_path), str(output_path)],
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            return output_path.read_text(encoding="utf-8")

    def test_json_decodes_entities_and_multiline_attributes(self):
        encoded_aliases = (
            "A&amp;B", "&quot;Quoted&quot;", "A&lt;B", "A&gt;B",
            "A&apos;B", "&#65;lias", "&#x41;lias", "&amp;amp;", "&#x4E2D;",
        )
        source = "<actor>" + "".join(
            f'<a\n zh_cn="Actor {index}"\n keyword="{alias}"/>'
            for index, alias in enumerate(encoded_aliases)
        ) + "</actor>"
        result = json.loads(self.convert(JSON_SCRIPT, source, "json"))
        self.assertEqual(
            [entry["a"][0] for entry in result],
            ["A&B", '"Quoted"', "A<B", "A>B", "A'B", "Alias", "Alias", "&amp;", "\u4e2d"],
        )

    def test_json_preserves_fallback_alias_order_and_empty_rules(self):
        source = (
            '<actor><a zh_cn="First" keyword=" A,A,\uff0c B ,A "/>'
            '<a zh_cn="Second" zh_tw="" jp="Japanese"/>'
            '<a keyword="Missing Chinese"/>'
            '<a zh_cn="" keyword=""/>'
            '<a zh_cn="" keyword=" Alias "/></actor>'
        )
        result = json.loads(self.convert(JSON_SCRIPT, source, "json"))
        self.assertEqual(result, [
            {"c": "First", "t": "First", "j": "First", "a": ["A", "B"]},
            {"c": "Second", "t": "", "j": "Japanese", "a": []},
            {"c": "", "t": "", "j": "", "a": ["Alias"]},
        ])

    def test_json_supports_wrapped_full_mapping(self):
        result = json.loads(self.convert(
            JSON_SCRIPT,
            '<actor-mapping><actor><a zh_cn="A"/></actor>'
            '<actor-blacklist>Keep out</actor-blacklist></actor-mapping>',
            "json",
        ))
        self.assertEqual(result, [{"c": "A", "t": "A", "j": "A", "a": []}])

    def test_simplified_xml_keeps_legacy_structure_and_only_four_fields(self):
        source = (
            '<actor-mapping><actor><a page_id="Ab" zh_cn="A&amp;B" '
            'jp="Name" keyword="&quot;Alias&quot;" tmdb_id="12" bio_graphy="Details"/>'
            '<a zh_tw="Only traditional"/></actor>'
            '<actor-blacklist>Keep out</actor-blacklist></actor-mapping>'
        )
        result = self.convert(XML_SCRIPT, source, "xml")
        self.assertEqual(result, (
            '<?xml version="1.0" encoding="UTF-8"?>\n<actor>\n'
            '  <a zh_cn="A&amp;B" jp="Name" keyword="&quot;Alias&quot;" />\n'
            '  <a zh_tw="Only traditional" />\n</actor>\n'
        ))

    def test_invalid_input_preserves_existing_outputs(self):
        for script in (JSON_SCRIPT, XML_SCRIPT):
            with self.subTest(script=script.name), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "invalid.xml"
                output = Path(directory) / "result"
                source.write_text('<actor><a zh_cn="Incomplete">', encoding="utf-8")
                output.write_text("Previous output", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(script), str(source), str(output)],
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output.read_text(encoding="utf-8"), "Previous output")

    def test_both_cli_commands_refuse_to_overwrite_source(self):
        for script in (JSON_SCRIPT, XML_SCRIPT):
            with self.subTest(script=script.name), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "source.xml"
                original = '<actor><a zh_cn="Keep"/></actor>'
                source.write_text(original, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(script), str(source), str(source)],
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(source.read_text(encoding="utf-8"), original)

    def test_repository_json_matches_decoded_full_mapping(self):
        source = (ROOT / "actor-mapping.xml").read_text(encoding="utf-8")
        root = ET.fromstring(source)
        actor = root if root.tag == "actor" else root.find("actor")
        expected = []
        for entry in actor:
            if entry.tag != "a" or "zh_cn" not in entry.attrib:
                continue
            name = entry.get("zh_cn")
            aliases = list(dict.fromkeys(
                part.strip() for part in re.split(r"[,\uff0c]", entry.get("keyword", ""))
                if part.strip()
            ))
            if not name and not aliases:
                continue
            expected.append({
                "c": name, "t": entry.get("zh_tw", name),
                "j": entry.get("jp", name), "a": aliases,
            })
        self.assertEqual(json.loads(self.convert(JSON_SCRIPT, source, "json")), expected)


if __name__ == "__main__":
    unittest.main()
