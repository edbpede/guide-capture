from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "lib" / "guide_capture.py"
WRAPPER = REPO_ROOT / "bin" / "guide-capture"
sys.path.insert(0, str(REPO_ROOT / "lib"))

from guide_capture import (  # noqa: E402
    AnnotationProcessingError,
    AnnotationSpecError,
    ProfileSpecError,
    build_ishoj_input_script,
    build_os2faktor_pin_script,
    find_matches,
    normalize_nodes,
    parse_foreground_package,
    parse_open_target,
    parse_package_version_code,
    parse_selector,
    process_annotation_spec,
    read_ishoj_credentials,
    read_os2faktor_pin,
    validate_annotation_spec,
    validate_profile,
    validate_public_text,
)


XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" content-desc="" resource-id="root" class="android.widget.FrameLayout"
    clickable="false" enabled="true" bounds="[0,0][1080,2400]">
    <node text="Filer" content-desc="" resource-id="dk.example:id/files"
      class="android.widget.TextView" clickable="true" enabled="true" focusable="true"
      focused="false" password="false" bounds="[10,20][110,80]" />
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
        self.assertTrue(files["focusable"])
        self.assertFalse(files["focused"])
        self.assertFalse(files["password"])

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

    def test_public_text_accepts_short_ascii_search_token(self) -> None:
        self.assertEqual(validate_public_text("Ish"), 3)

    def test_public_text_rejects_spaces_unicode_and_shell_metacharacters(self) -> None:
        for value in ("Ishøj", "Ish kommune", "Ish;id", "$(id)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_public_text(value)

    def test_ishoj_credentials_require_private_file_and_supported_values(self) -> None:
        env_path = self.temporary_path / ".env"
        env_path.write_text(
            "I_ACC_EMAIL=user@example.invalid\nI_ACC_PASS=Safe!Pass123\n",
            encoding="utf-8",
        )
        env_path.chmod(0o600)
        self.assertEqual(
            read_ishoj_credentials(env_path),
            ("user@example.invalid", "Safe!Pass123"),
        )
        env_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "mode 600"):
            read_ishoj_credentials(env_path)

    def test_ishoj_input_script_requires_exact_empty_password_metadata(self) -> None:
        nodes = [
            {
                "text": "",
                "resource_id": "username",
                "class": "android.widget.EditText",
                "clickable": True,
                "enabled": True,
                "focusable": True,
                "password": False,
                "center": {"x": 100, "y": 200},
            },
            {
                "text": "",
                "resource_id": "password",
                "class": "android.widget.EditText",
                "clickable": True,
                "enabled": True,
                "focusable": True,
                "password": True,
                "center": {"x": 100, "y": 300},
            },
        ]
        script = build_ishoj_input_script(nodes, "user@example.invalid", "Safe!Pass123")
        self.assertIn("input tap 100 200", script)
        self.assertIn("input text user@example.invalid", script)
        self.assertIn("input tap 100 300", script)
        self.assertIn("input text 'Safe!Pass123'", script)

        nodes[1]["password"] = False
        with self.assertRaisesRegex(ValueError, "unsafe"):
            build_ishoj_input_script(nodes, "user@example.invalid", "Safe!Pass123")

    def test_os2faktor_pin_requires_six_digits_and_builds_semantic_taps(self) -> None:
        env_path = self.temporary_path / ".env"
        env_path.write_text("OS2FAKTOR_PIN=123001\n", encoding="utf-8")
        env_path.chmod(0o600)
        pin = read_os2faktor_pin(env_path)
        nodes = [
            {
                "text": "Angiv pinkode",
                "enabled": True,
                "class": "android.widget.TextView",
                "center": {"x": 0, "y": 0},
            }
        ]
        nodes.extend(
            {
                "text": digit,
                "enabled": True,
                "class": "android.view.View",
                "center": {"x": int(digit) * 10, "y": 500},
            }
            for digit in "0123"
        )
        script = build_os2faktor_pin_script(nodes, pin)
        self.assertEqual(script.count("input tap"), 6)
        self.assertTrue(script.startswith("input tap 10 500\n"))

        env_path.write_text("OS2FAKTOR_PIN=12345x\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "six ASCII digits"):
            read_os2faktor_pin(env_path)

    def test_package_version_code_allows_android_indentation(self) -> None:
        output = "    versionCode=30201 minSdk=23 targetSdk=35\n"
        self.assertEqual(parse_package_version_code(output), "30201")

    def test_open_target_accepts_https_and_lowercase_package(self) -> None:
        self.assertEqual(
            parse_open_target("https://aula.dk/"),
            {"type": "url", "value": "https://aula.dk/"},
        )
        self.assertEqual(
            parse_open_target("dk.digitalidentity.os2faktor"),
            {"type": "package", "value": "dk.digitalidentity.os2faktor"},
        )

    def test_open_target_rejects_insecure_or_credential_bearing_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            parse_open_target("http://aula.dk/")
        with self.assertRaisesRegex(ValueError, "must not contain credentials"):
            parse_open_target("https://user:secret@aula.dk/")

    def test_open_target_rejects_shell_or_package_injection(self) -> None:
        with self.assertRaisesRegex(ValueError, "package target"):
            parse_open_target("dk.digitalidentity.os2faktor;id")

    def test_foreground_package_parses_android_activity_state(self) -> None:
        output = (
            "mResumedActivity: ActivityRecord{123 u0 "
            "com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity t42}\n"
        )
        self.assertEqual(parse_foreground_package(output), "com.android.chrome")

    def test_pinned_profile_and_tracked_specs_are_valid(self) -> None:
        profile = json.loads(
            (REPO_ROOT / "profiles" / "android-phone.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_profile(profile)["profile"], "android-phone")
        for spec_path in (REPO_ROOT / "specs").glob("*.json"):
            with self.subTest(spec=spec_path.name):
                validate_annotation_spec(json.loads(spec_path.read_text(encoding="utf-8")))

    def test_profile_rejects_unknown_or_malformed_pinned_values(self) -> None:
        profile_path = REPO_ROOT / "profiles" / "android-phone.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["schema_version"] = 1.0
        with self.assertRaisesRegex(ProfileSpecError, "schema_version must be 1"):
            validate_profile(profile)

        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["system_image"]["revision"] = 7
        with self.assertRaisesRegex(ProfileSpecError, "revision must be a non-empty string"):
            validate_profile(profile)

        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["packages"]["chrome"]["unexpected"] = True
        with self.assertRaisesRegex(ProfileSpecError, "unsupported key: unexpected"):
            validate_profile(profile)


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

    def test_start_value_must_be_safe_and_match_its_declared_type(self) -> None:
        spec = self.valid_spec()
        spec["start"] = {"type": "url", "value": "dk.digitalidentity.os2faktor"}
        with self.assertRaisesRegex(AnnotationSpecError, "type does not match"):
            validate_annotation_spec(spec)

        spec["start"] = {"type": "url", "value": "http://example.invalid/"}
        with self.assertRaisesRegex(AnnotationSpecError, "must use HTTPS"):
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
        self.assertEqual(result["images"][0]["input"], f"{self.raw_dir.name}/{source.name}")
        self.assertEqual(result["images"][0]["output"], f"pilot-guide/{output.name}")
        self.assertTrue(result["human_review_required"])

    def test_report_records_relative_paths_only(self) -> None:
        # The report ships beside published screenshots, so an absolute path would leak the
        # operator's home directory and account name into the guides repository.
        self.make_source()
        self.write_spec(self.valid_spec())

        process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)

        report_text = (self.reviewed_root / "pilot-guide" / "annotation-report.json").read_text(
            encoding="utf-8"
        )
        for path_field in ('"input":', '"output":'):
            self.assertIn(path_field, report_text)
        self.assertNotIn(str(self.temporary_path), report_text)
        self.assertNotIn(str(Path.home()), report_text)
        for record in json.loads(report_text)["images"]:
            self.assertFalse(Path(record["input"]).is_absolute())
            self.assertFalse(Path(record["output"]).is_absolute())

    def test_pipeline_refuses_to_overwrite_reviewed_output(self) -> None:
        self.make_source()
        spec = self.valid_spec()
        spec["steps"][0]["annotate"]["arrow_from"] = [100, 100]
        self.write_spec(spec)
        process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)
        with self.assertRaisesRegex(AnnotationProcessingError, "annotation report already exists"):
            process_annotation_spec(self.spec_path, self.raw_dir, self.reviewed_root, self.magick)

        completed = subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "annotate",
                str(self.spec_path),
                str(self.raw_dir),
                str(self.reviewed_root),
                str(self.magick),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 73)
        self.assertFalse(json.loads(completed.stdout)["ok"])

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

    def test_worked_example_hashes_match_its_report(self) -> None:
        examples_root = REPO_ROOT / "examples"
        report_path = (
            examples_root / "hvordan-bruger-jeg-os2faktor" / "annotation-report.json"
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(report["human_review_required"])
        for image in report["images"]:
            output = examples_root / image["output"]
            with self.subTest(output=image["output"]):
                self.assertTrue(output.is_file())
                self.assertEqual(
                    hashlib.sha256(output.read_bytes()).hexdigest(),
                    image["output_sha256"],
                )


class WrapperContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_path = Path(self.temporary_directory.name)
        self.private_root = self.temporary_path / "private"
        self.environment = os.environ.copy()
        self.environment["GUIDE_CAPTURE_PRIVATE"] = str(self.private_root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_wrapper(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(WRAPPER), *arguments],
            cwd=REPO_ROOT,
            env=self.environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_annotate_rejects_a_spec_outside_the_repository_spec_directory(self) -> None:
        spec = self.temporary_path / "outside.json"
        spec.write_text("{}\n", encoding="utf-8")
        completed = self.run_wrapper("annotate", str(spec))
        self.assertEqual(completed.returncode, 64)
        result = json.loads(completed.stdout)
        self.assertEqual(result["command"], "annotate")
        self.assertIn("inside specs/", result["error"])

    def test_validate_accepts_the_tracked_spec_before_boot(self) -> None:
        completed = self.run_wrapper(
            "validate", "specs/hvordan-bruger-jeg-os2faktor.android.json"
        )
        self.assertEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(result["command"], "validate")
        self.assertEqual(result["steps"], 7)

    def test_kill_rejects_state_whose_run_directory_is_outside_the_private_root(self) -> None:
        unsafe_run = self.temporary_path / "android-unsafe"
        unsafe_run.mkdir()
        runtime = self.private_root / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "current-run.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": "android-unsafe",
                    "run_dir": str(unsafe_run),
                    "avd_home": str(unsafe_run / "avd"),
                    "avd_name": "edb-phone-run-unsafe",
                    "serial": "emulator-5556",
                    "emulator_pid": 999999,
                }
            ),
            encoding="utf-8",
        )
        completed = self.run_wrapper("kill", "android")
        self.assertEqual(completed.returncode, 65)
        self.assertEqual(json.loads(completed.stdout)["error"], "current run directory is invalid")
        self.assertTrue(unsafe_run.is_dir())


if __name__ == "__main__":
    unittest.main()
