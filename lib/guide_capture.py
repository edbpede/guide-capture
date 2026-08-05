#!/usr/bin/env python3
"""Small helpers for the guide-capture shell wrapper."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


BOUNDS_RE = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")
VERSION_CODE_RE = re.compile(r"\bversionCode=(\d+)\b")
SELECTOR_KEYS = {"text", "content_desc", "resource_id"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STEP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
FOREGROUND_MARKERS = ("mResumedActivity", "topResumedActivity")
FOREGROUND_PACKAGE_RE = re.compile(r"(?:\bu\d+\s+)?([A-Za-z][A-Za-z0-9_.]*)/[A-Za-z0-9_.$]+")
COVER_COLOR = "#20242B"
HIGHLIGHT_COLOR = "#F5C518"
BADGE_COLOR = "#C62828"
FONT_CANDIDATES = (
    Path("/System/Library/Fonts/SFNS.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


class AnnotationSpecError(ValueError):
    """Raised when an annotation specification is unsafe or incomplete."""


class AnnotationProcessingError(RuntimeError):
    """Raised when an image cannot be inspected or transformed."""


def parse_bounds(raw: str) -> tuple[list[int], dict[str, int]] | None:
    match = BOUNDS_RE.fullmatch(raw)
    if not match:
        return None
    left, top, right, bottom = (int(value) for value in match.groups())
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom], {
        "x": (left + right) // 2,
        "y": (top + bottom) // 2,
    }


def normalize_nodes(xml_path: Path) -> list[dict[str, object]]:
    root = ET.parse(xml_path).getroot()
    nodes: list[dict[str, object]] = []
    for element in root.iter("node"):
        parsed_bounds = parse_bounds(element.attrib.get("bounds", ""))
        if parsed_bounds is None:
            continue
        bounds, center = parsed_bounds
        nodes.append(
            {
                "text": element.attrib.get("text", ""),
                "content_desc": element.attrib.get("content-desc", ""),
                "resource_id": element.attrib.get("resource-id", ""),
                "class": element.attrib.get("class", ""),
                "clickable": element.attrib.get("clickable") == "true",
                "enabled": element.attrib.get("enabled") == "true",
                "bounds": bounds,
                "center": center,
            }
        )
    return nodes


def parse_selector(raw: str) -> dict[str, str]:
    try:
        selector = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"selector is not valid JSON: {error.msg}") from error
    if not isinstance(selector, dict) or set(selector) not in ({key} for key in SELECTOR_KEYS):
        supported = ", ".join(sorted(SELECTOR_KEYS))
        raise ValueError(f"selector must contain exactly one of: {supported}")
    key, value = next(iter(selector.items()))
    if not isinstance(value, str) or not value:
        raise ValueError("selector value must be a non-empty string")
    return {key: value}


def find_matches(nodes: list[dict[str, object]], selector: dict[str, str]) -> list[dict[str, object]]:
    key, value = next(iter(selector.items()))
    return [node for node in nodes if node["enabled"] and node[key] == value]


def parse_package_version_code(output: str) -> str:
    match = VERSION_CODE_RE.search(output)
    if not match:
        raise ValueError("package output does not contain versionCode")
    return match.group(1)


def parse_open_target(raw: str) -> dict[str, str]:
    if not raw or any(character.isspace() for character in raw):
        raise ValueError("open target must be one URL or package name without whitespace")
    if raw.startswith("https://"):
        parsed = urlsplit(raw)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("URL target must be an absolute HTTPS URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("URL target must not contain credentials")
        return {"type": "url", "value": raw}
    if "://" in raw:
        raise ValueError("URL target must use HTTPS")
    if not PACKAGE_RE.fullmatch(raw):
        raise ValueError("package target is not a valid lowercase Android package name")
    return {"type": "package", "value": raw}


def parse_foreground_package(output: str) -> str:
    for line in output.splitlines():
        if not any(marker in line for marker in FOREGROUND_MARKERS):
            continue
        match = FOREGROUND_PACKAGE_RE.search(line)
        if match:
            return match.group(1)
    raise ValueError("foreground package was not reported")


def _require_object(value: object, location: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AnnotationSpecError(f"{location} must be an object")
    return value


def _require_exact_keys(
    value: dict[str, object], location: str, required: set[str], optional: set[str] | None = None
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise AnnotationSpecError(f"{location} is missing required key: {sorted(missing)[0]}")
    if unknown:
        raise AnnotationSpecError(f"{location} contains unsupported key: {sorted(unknown)[0]}")


def _validate_bounds(value: object, location: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise AnnotationSpecError(f"{location} must be four integer coordinates")
    left, top, right, bottom = value
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise AnnotationSpecError(f"{location} must be a non-empty [left, top, right, bottom] region")
    return value


def _validate_point(value: object, location: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
        or any(item < 0 for item in value)
    ):
        raise AnnotationSpecError(f"{location} must be two non-negative integer coordinates")
    return value


def _validate_selector(value: object, location: str) -> dict[str, str]:
    selector = _require_object(value, location)
    try:
        return parse_selector(json.dumps(selector))
    except ValueError as error:
        raise AnnotationSpecError(f"{location}: {error}") from error


def validate_annotation_spec(value: object) -> dict[str, object]:
    spec = _require_object(value, "spec")
    _require_exact_keys(spec, "spec", {"schema_version", "slug", "start", "steps"})
    if (
        not isinstance(spec["schema_version"], int)
        or isinstance(spec["schema_version"], bool)
        or spec["schema_version"] != 1
    ):
        raise AnnotationSpecError("spec.schema_version must be 1")

    slug = spec["slug"]
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        raise AnnotationSpecError("spec.slug must be a lowercase URL-safe slug")

    start = _require_object(spec["start"], "spec.start")
    _require_exact_keys(start, "spec.start", {"type", "value"})
    if not isinstance(start["type"], str) or start["type"] not in {"url", "package"}:
        raise AnnotationSpecError("spec.start.type must be url or package")
    if not isinstance(start["value"], str) or not start["value"].strip():
        raise AnnotationSpecError("spec.start.value must be a non-empty string")

    steps = spec["steps"]
    if not isinstance(steps, list) or not steps:
        raise AnnotationSpecError("spec.steps must be a non-empty array")

    seen_ids: set[str] = set()
    for index, raw_step in enumerate(steps):
        location = f"spec.steps[{index}]"
        step = _require_object(raw_step, location)
        _require_exact_keys(
            step,
            location,
            {"id", "redact"},
            {"find", "expect_after", "annotate"},
        )
        step_id = step["id"]
        if not isinstance(step_id, str) or not STEP_ID_RE.fullmatch(step_id):
            raise AnnotationSpecError(f"{location}.id contains unsupported characters")
        if step_id in seen_ids:
            raise AnnotationSpecError(f"{location}.id is duplicated: {step_id}")
        seen_ids.add(step_id)

        for selector_name in ("find", "expect_after"):
            if selector_name in step:
                _validate_selector(step[selector_name], f"{location}.{selector_name}")

        redactions = step["redact"]
        if not isinstance(redactions, list):
            raise AnnotationSpecError(f"{location}.redact must be an array, including when empty")
        for redaction_index, raw_redaction in enumerate(redactions):
            redaction_location = f"{location}.redact[{redaction_index}]"
            redaction = _require_object(raw_redaction, redaction_location)
            _require_exact_keys(redaction, redaction_location, {"bounds", "reason"})
            _validate_bounds(redaction["bounds"], f"{redaction_location}.bounds")
            if not isinstance(redaction["reason"], str) or not redaction["reason"].strip():
                raise AnnotationSpecError(f"{redaction_location}.reason must be a non-empty string")

        if "annotate" in step:
            annotation = _require_object(step["annotate"], f"{location}.annotate")
            _require_exact_keys(
                annotation,
                f"{location}.annotate",
                {"type", "bounds", "number"},
                {"arrow_from"},
            )
            if annotation["type"] != "highlight":
                raise AnnotationSpecError(f"{location}.annotate.type must be highlight")
            _validate_bounds(annotation["bounds"], f"{location}.annotate.bounds")
            number = annotation["number"]
            if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= 99:
                raise AnnotationSpecError(f"{location}.annotate.number must be an integer from 1 to 99")
            if "arrow_from" in annotation:
                _validate_point(annotation["arrow_from"], f"{location}.annotate.arrow_from")
    return spec


def load_annotation_spec(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AnnotationSpecError(f"spec is not valid JSON: {error.msg}") from error
    except OSError as error:
        raise AnnotationSpecError(f"could not read spec: {error}") from error
    return validate_annotation_spec(value)


def _run_magick(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        raise AnnotationProcessingError(f"ImageMagick failed: {detail}") from error


def _image_dimensions(magick: Path, image: Path) -> tuple[int, int]:
    result = _run_magick([str(magick), "identify", "-format", "%w %h", str(image)])
    try:
        width, height = (int(value) for value in result.stdout.split())
    except ValueError as error:
        raise AnnotationProcessingError("ImageMagick returned invalid image dimensions") from error
    return width, height


def _validate_coordinates(step: dict[str, object], width: int, height: int, location: str) -> None:
    def require_in_image(bounds: list[int], bounds_location: str) -> None:
        if bounds[2] > width or bounds[3] > height:
            raise AnnotationSpecError(f"{bounds_location} exceeds the {width}x{height} source image")

    for index, redaction in enumerate(step["redact"]):
        require_in_image(redaction["bounds"], f"{location}.redact[{index}].bounds")
    if "annotate" in step:
        annotation = step["annotate"]
        require_in_image(annotation["bounds"], f"{location}.annotate.bounds")
        if "arrow_from" in annotation:
            x, y = annotation["arrow_from"]
            if x >= width or y >= height:
                raise AnnotationSpecError(
                    f"{location}.annotate.arrow_from exceeds the {width}x{height} source image"
                )


def _arrow_draw(from_point: list[int], to_point: tuple[int, int]) -> str:
    start_x, start_y = from_point
    end_x, end_y = to_point
    angle = math.atan2(end_y - start_y, end_x - start_x)
    head_length = 24
    spread = math.pi / 7
    left = (
        round(end_x - head_length * math.cos(angle - spread)),
        round(end_y - head_length * math.sin(angle - spread)),
    )
    right = (
        round(end_x - head_length * math.cos(angle + spread)),
        round(end_y - head_length * math.sin(angle + spread)),
    )
    return (
        f"line {start_x},{start_y} {end_x},{end_y} "
        f"polygon {end_x},{end_y} {left[0]},{left[1]} {right[0]},{right[1]}"
    )


def _font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise AnnotationProcessingError("no supported annotation font is installed")


def _magick_annotation_command(
    magick: Path,
    source: Path,
    destination: Path,
    step: dict[str, object],
    width: int,
    height: int,
) -> list[str]:
    command = [str(magick), str(source)]
    for redaction in step["redact"]:
        left, top, right, bottom = redaction["bounds"]
        command.extend(
            [
                "-fill",
                COVER_COLOR,
                "-stroke",
                "none",
                "-draw",
                f"rectangle {left},{top} {right - 1},{bottom - 1}",
            ]
        )

    if "annotate" in step:
        annotation = step["annotate"]
        left, top, right, bottom = annotation["bounds"]
        center = ((left + right) // 2, (top + bottom) // 2)
        if "arrow_from" in annotation:
            command.extend(
                [
                    "-fill",
                    HIGHLIGHT_COLOR,
                    "-stroke",
                    HIGHLIGHT_COLOR,
                    "-strokewidth",
                    "8",
                    "-draw",
                    _arrow_draw(annotation["arrow_from"], center),
                ]
            )
        command.extend(
            [
                "-fill",
                "none",
                "-stroke",
                HIGHLIGHT_COLOR,
                "-strokewidth",
                "8",
                "-draw",
                f"roundrectangle {left},{top} {right - 1},{bottom - 1} 18,18",
            ]
        )

        radius = max(10, min(26, min(width, height) // 12))
        badge_x = min(max(left, radius + 2), width - radius - 2)
        badge_y = min(max(top, radius + 2), height - radius - 2)
        command.extend(
            [
                "-fill",
                BADGE_COLOR,
                "-stroke",
                "white",
                "-strokewidth",
                "3",
                "-draw",
                f"circle {badge_x},{badge_y} {badge_x + radius},{badge_y}",
                "-font",
                str(_font_path()),
                "-fill",
                "white",
                "-stroke",
                "none",
                "-pointsize",
                str(round(radius * 1.3)),
                "-gravity",
                "northwest",
                "-draw",
                f"text-anchor middle text {badge_x},{badge_y + round(radius * 0.4)} '{annotation['number']}'",
            ]
        )

    command.extend(
        [
            "-strip",
            "-define",
            "png:exclude-chunks=date,time",
            "-define",
            "png:compression-level=9",
            str(destination),
        ]
    )
    return command


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def process_annotation_spec(
    spec_path: Path, raw_dir: Path, reviewed_root: Path, magick: Path
) -> dict[str, object]:
    spec = load_annotation_spec(spec_path)
    if reviewed_root.is_symlink():
        raise AnnotationProcessingError("reviewed output root must not be a symbolic link")
    raw_root = raw_dir.resolve(strict=True)
    if not raw_root.is_dir():
        raise AnnotationProcessingError("raw capture path is not a directory")
    if not magick.is_file() or not os.access(magick, os.X_OK):
        raise AnnotationProcessingError("ImageMagick executable is missing")

    reviewed_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(reviewed_root, 0o700)
    output_dir = reviewed_root / spec["slug"]
    if output_dir.is_symlink():
        raise AnnotationProcessingError("per-guide reviewed output must not be a symbolic link")
    if output_dir.exists() and output_dir.resolve().parent != reviewed_root.resolve():
        raise AnnotationProcessingError("reviewed output path escapes the workspace")
    report_path = output_dir / "annotation-report.json"
    if report_path.exists():
        raise AnnotationProcessingError("annotation report already exists; review or remove it explicitly")

    jobs: list[tuple[dict[str, object], Path, Path, int, int]] = []
    for index, step in enumerate(spec["steps"]):
        source = raw_root / f"{step['id']}.png"
        if not source.is_file() or source.resolve().parent != raw_root:
            raise AnnotationProcessingError(f"raw capture is missing for step {step['id']}")
        destination = output_dir / f"{step['id']}.android.png"
        if destination.exists():
            raise AnnotationProcessingError(f"reviewed output already exists for step {step['id']}")
        width, height = _image_dimensions(magick, source)
        _validate_coordinates(step, width, height, f"spec.steps[{index}]")
        jobs.append((step, source, destination, width, height))

    report_images: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="annotate-", dir=reviewed_root) as temporary:
        temporary_path = Path(temporary)
        staged_outputs: list[tuple[Path, Path]] = []
        for step, source, destination, width, height in jobs:
            staged = temporary_path / destination.name
            _run_magick(_magick_annotation_command(magick, source, staged, step, width, height))
            os.chmod(staged, 0o600)
            report_images.append(
                {
                    "id": step["id"],
                    "input": str(source),
                    "output": str(destination),
                    "dimensions": f"{width}x{height}",
                    "input_sha256": _sha256(source),
                    "output_sha256": _sha256(staged),
                    "redactions": len(step["redact"]),
                    "annotated": "annotate" in step,
                }
            )
            staged_outputs.append((staged, destination))

        report: dict[str, object] = {
            "schema_version": 1,
            "slug": spec["slug"],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "images": report_images,
            "human_review_required": True,
        }
        staged_report = temporary_path / report_path.name
        staged_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(staged_report, 0o600)

        output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(output_dir, 0o700)
        for staged, destination in staged_outputs:
            staged.replace(destination)
        staged_report.replace(report_path)

    return {
        "ok": True,
        "command": "annotate",
        "slug": spec["slug"],
        "images": report_images,
        "report": str(report_path),
        "human_review_required": True,
    }


def command_normalize(args: argparse.Namespace) -> int:
    nodes = normalize_nodes(Path(args.xml))
    output = Path(args.output)
    output.write_text(json.dumps(nodes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(nodes), "output": str(output)}))
    return 0


def command_match(args: argparse.Namespace) -> int:
    try:
        selector = parse_selector(args.selector)
        nodes = json.loads(Path(args.nodes).read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 64
    matches = find_matches(nodes, selector)
    print(
        json.dumps(
            {"ok": len(matches) == 1, "selector": selector, "count": len(matches), "matches": matches},
            ensure_ascii=False,
        )
    )
    return 0 if len(matches) == 1 else 2 if not matches else 3


def command_package_version_code(_args: argparse.Namespace) -> int:
    try:
        print(parse_package_version_code(sys.stdin.read()))
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 65
    return 0


def command_open_target(args: argparse.Namespace) -> int:
    try:
        print(json.dumps(parse_open_target(args.target)))
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 64
    return 0


def command_foreground_package(_args: argparse.Namespace) -> int:
    try:
        print(parse_foreground_package(sys.stdin.read()))
    except ValueError:
        return 2
    return 0


def update_key_value(path: Path, replacements: dict[str, str]) -> None:
    if not path.exists():
        return
    updated: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0].strip()
        updated.append(f"{key} = {replacements[key]}" if key in replacements else line)
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def command_rewrite_avd(args: argparse.Namespace) -> int:
    avd_dir = Path(args.avd_dir).resolve()
    avd_home = Path(args.avd_home).resolve()
    if avd_dir.parent != avd_home or avd_dir.name != f"{args.new_name}.avd":
        print(json.dumps({"ok": False, "error": "AVD path does not match the requested run name"}))
        return 64

    update_key_value(
        avd_dir / "hardware-qemu.ini",
        {
            "disk.cachePartition.path": str(avd_dir / "cache.img"),
            "disk.dataPartition.path": str(avd_dir / "userdata-qemu.img"),
            "disk.encryptionKeyPartition.path": str(avd_dir / "encryptionkey.img"),
            "avd.name": args.new_name,
            "avd.id": args.new_name,
            "android.avd.home": str(avd_home),
        },
    )

    config = avd_dir / "config.ini"
    update_key_value(config, {"AvdId": args.new_name, "avd.ini.displayname": args.new_name})

    launch_params = avd_dir / "emu-launch-params.txt"
    if launch_params.exists():
        lines = launch_params.read_text(encoding="utf-8").splitlines()
        launch_params.write_text(
            "\n".join(args.new_name if line == args.old_name else line for line in lines) + "\n",
            encoding="utf-8",
        )

    print(json.dumps({"ok": True, "avd_dir": str(avd_dir), "avd_name": args.new_name}))
    return 0


def command_annotate(args: argparse.Namespace) -> int:
    try:
        result = process_annotation_spec(
            Path(args.spec), Path(args.raw_dir), Path(args.reviewed_root), Path(args.magick)
        )
    except AnnotationSpecError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 64
    except AnnotationProcessingError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 65
    except OSError as error:
        print(json.dumps({"ok": False, "error": f"file operation failed: {error}"}))
        return 66
    print(json.dumps(result, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize")
    normalize.add_argument("xml")
    normalize.add_argument("output")
    normalize.set_defaults(handler=command_normalize)

    match = subparsers.add_parser("match")
    match.add_argument("nodes")
    match.add_argument("selector")
    match.set_defaults(handler=command_match)

    version_code = subparsers.add_parser("package-version-code")
    version_code.set_defaults(handler=command_package_version_code)

    open_target = subparsers.add_parser("open-target")
    open_target.add_argument("target")
    open_target.set_defaults(handler=command_open_target)

    foreground_package = subparsers.add_parser("foreground-package")
    foreground_package.set_defaults(handler=command_foreground_package)

    rewrite = subparsers.add_parser("rewrite-avd")
    rewrite.add_argument("avd_dir")
    rewrite.add_argument("old_name")
    rewrite.add_argument("new_name")
    rewrite.add_argument("avd_home")
    rewrite.set_defaults(handler=command_rewrite_avd)

    annotate = subparsers.add_parser("annotate")
    annotate.add_argument("spec")
    annotate.add_argument("raw_dir")
    annotate.add_argument("reviewed_root")
    annotate.add_argument("magick")
    annotate.set_defaults(handler=command_annotate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
