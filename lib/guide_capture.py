#!/usr/bin/env python3
"""Small helpers for the guide-capture shell wrapper."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


BOUNDS_RE = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")
VERSION_CODE_RE = re.compile(r"\bversionCode=(\d+)\b")
SELECTOR_KEYS = {"text", "content_desc", "resource_id"}


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

    rewrite = subparsers.add_parser("rewrite-avd")
    rewrite.add_argument("avd_dir")
    rewrite.add_argument("old_name")
    rewrite.add_argument("new_name")
    rewrite.add_argument("avd_home")
    rewrite.set_defaults(handler=command_rewrite_avd)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
