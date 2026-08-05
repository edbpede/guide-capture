from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from guide_capture import (  # noqa: E402
    find_matches,
    normalize_nodes,
    parse_package_version_code,
    parse_selector,
)


XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" content-desc="" resource-id="root" class="android.widget.FrameLayout"
    clickable="false" enabled="true" bounds="[0,0][1080,2400]">
    <node text="Filer" content-desc="" resource-id="dk.example:id/files"
      class="android.widget.TextView" clickable="true" enabled="true" bounds="[10,20][110,80]" />
    <node text="Filer" content-desc="disabled" resource-id="dk.example:id/disabled"
      class="android.widget.TextView" clickable="true" enabled="false" bounds="[10,90][110,150]" />
  </node>
</hierarchy>
"""


class GuideCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.xml_path = Path(self.temporary_directory.name) / "window.xml"
        self.xml_path.write_text(XML, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_normalize_calculates_center_and_booleans(self) -> None:
        nodes = normalize_nodes(self.xml_path)
        files = next(node for node in nodes if node["resource_id"] == "dk.example:id/files")
        self.assertEqual(files["bounds"], [10, 20, 110, 80])
        self.assertEqual(files["center"], {"x": 60, "y": 50})
        self.assertTrue(files["enabled"])
        self.assertTrue(files["clickable"])

    def test_exact_selector_ignores_disabled_match(self) -> None:
        nodes = normalize_nodes(self.xml_path)
        matches = find_matches(nodes, parse_selector('{"text":"Filer"}'))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["resource_id"], "dk.example:id/files")

    def test_selector_requires_one_supported_key(self) -> None:
        with self.assertRaises(ValueError):
            parse_selector('{"text":"Filer","resource_id":"dk.example:id/files"}')

    def test_duplicate_enabled_nodes_are_ambiguous(self) -> None:
        nodes = normalize_nodes(self.xml_path)
        duplicate = dict(next(node for node in nodes if node["resource_id"] == "dk.example:id/files"))
        duplicate["resource_id"] = "dk.example:id/files-copy"
        matches = find_matches(nodes + [duplicate], parse_selector('{"text":"Filer"}'))
        self.assertEqual(len(matches), 2)

    def test_package_version_code_allows_android_indentation(self) -> None:
        output = "    versionCode=30201 minSdk=23 targetSdk=35\n"
        self.assertEqual(parse_package_version_code(output), "30201")


if __name__ == "__main__":
    unittest.main()
