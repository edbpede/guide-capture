from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from guide_capture import (  # noqa: E402
    AnnotationProcessingError,
    AnnotationSpecError,
    find_matches,
    normalize_nodes,
    parse_package_version_code,
    parse_selector,
    process_annotation_spec,
    validate_annotation_spec,
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
        self.temporary_path = Path(self.temporary_directory.name)
        self.xml_path = self.temporary_path / "window.xml"
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


class AnnotationPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_path = Path(self.temporary_directory.name)
        self.raw_dir = self.temporary_path / "raw"
        self.reviewed_root = self.temporary_path / "reviewed"
        self.spec_path = self.temporary_path / "spec.json"
        self.magick = Path("/opt/homebrew/bin/magick")
        self.raw_dir.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def valid_spec() -> dict[str, object]:
        return {
            "schema_version": 1,
            "slug": "pilot-guide",
            "start": {"type": "url", "value": "https://example.invalid/"},
            "steps": [
                {
                    "id": "02",
                    "find": {"text": "Filer"},
                    "expect_after": {"text": "Sikre filer"},
                    "redact": [
                        {"bounds": [20, 20, 80, 80], "reason": "fixture identity"}
                    ],
                    "annotate": {
                        "type": "highlight",
                        "bounds": [20, 20, 80, 80],
                        "number": 2,
                    },
                }
            ],
        }

    def write_spec(self, value: object) -> None:
        self.spec_path.write_text(json.dumps(value), encoding="utf-8")

    def make_source(self) -> Path:
        source = self.raw_dir / "02.png"
        subprocess.run(
            [
                str(self.magick),
                "-size",
                "120x120",
                "xc:white",
                "-set",
                "comment",
                "must-not-survive",
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return source

    def pixel(self, image: Path, x: int, y: int) -> str:
        result = subprocess.run(
            [str(self.magick), str(image), "-format", f"%[pixel:p{{{x},{y}}}]", "info:"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def color_pixel(self, color: str) -> str:
        result = subprocess.run(
            [str(self.magick), "-size", "1x1", f"xc:{color}", "-format", "%[pixel:p{0,0}]", "info:"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def test_redact_key_is_mandatory_even_when_no_regions_are_needed(self) -> None:
        spec = self.valid_spec()
        del spec["steps"][0]["redact"]
        with self.assertRaisesRegex(AnnotationSpecError, "missing required key: redact"):
            validate_annotation_spec(spec)

    def test_malformed_start_type_is_a_schema_error(self) -> None:
        spec = self.valid_spec()
        spec["start"]["type"] = []
        with self.assertRaisesRegex(AnnotationSpecError, "start.type must be url or package"):
            validate_annotation_spec(spec)

    def test_coordinates_must_fit_the_source_before_output_is_written(self) -> None:
        self.make_source()
        spec = self.valid_spec()
        spec["steps"][0]["redact"][0]["bounds"] = [20, 20, 121, 80]
        self.write_spec(spec)
        with self.assertRaisesRegex(AnnotationSpecError, "exceeds the 120x120 source image"):
            process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)
        self.assertFalse((self.reviewed_root / "pilot-guide" / "02.android.png").exists())

    def test_pipeline_redacts_before_annotation_strips_metadata_and_records_hashes(self) -> None:
        source = self.make_source()
        self.write_spec(self.valid_spec())

        result = process_annotation_spec(
            self.spec_path, self.raw_dir, self.reviewed_root, self.magick
        )

        output = self.reviewed_root / "pilot-guide" / "02.android.png"
        report = self.reviewed_root / "pilot-guide" / "annotation-report.json"
        self.assertTrue(output.is_file())
        self.assertTrue(report.is_file())
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(self.pixel(output, 50, 50), self.color_pixel("#20242B"))
        self.assertEqual(self.pixel(output, 20, 50), self.color_pixel("#F5C518"))

        comment = subprocess.run(
            [str(self.magick), "identify", "-format", "%c", str(output)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(comment, "")
        self.assertNotEqual(result["images"][0]["input_sha256"], result["images"][0]["output_sha256"])
        self.assertEqual(result["images"][0]["input"], str(source.resolve()))
        self.assertTrue(result["human_review_required"])

    def test_pipeline_refuses_to_overwrite_reviewed_output(self) -> None:
        self.make_source()
        spec = self.valid_spec()
        spec["steps"][0]["annotate"]["arrow_from"] = [100, 100]
        self.write_spec(spec)
        process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)
        with self.assertRaisesRegex(AnnotationProcessingError, "annotation report already exists"):
            process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)

    def test_pipeline_rejects_a_symlinked_review_root(self) -> None:
        self.make_source()
        self.write_spec(self.valid_spec())
        actual_reviewed = self.temporary_path / "redirected"
        actual_reviewed.mkdir()
        self.reviewed_root.symlink_to(actual_reviewed, target_is_directory=True)
        with self.assertRaisesRegex(AnnotationProcessingError, "must not be a symbolic link"):
            process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)

    def test_pipeline_rejects_a_symlinked_guide_output(self) -> None:
        self.make_source()
        self.write_spec(self.valid_spec())
        self.reviewed_root.mkdir()
        redirected = self.reviewed_root / "redirected"
        redirected.mkdir()
        (self.reviewed_root / "pilot-guide").symlink_to(redirected, target_is_directory=True)
        with self.assertRaisesRegex(AnnotationProcessingError, "per-guide reviewed output"):
            process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)


if __name__ == "__main__":
    unittest.main()
