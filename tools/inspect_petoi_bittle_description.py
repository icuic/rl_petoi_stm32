#!/usr/bin/env python3
"""Summarize the fetched Petoi Bittle ROS description."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


DEFAULT_MODEL_DIR = Path(
    "third_party/petoi/ros_opencat/"
    "petoi_ROS_model_docs/bittle_ros/bittle_description"
)


def _count_tags(text: str, tag: str) -> int:
    return len(re.findall(rf"<\s*{re.escape(tag)}(?:\s|>|/)", text))


def _attr_values(text: str, tag: str, attr: str) -> list[str]:
    pattern = rf"<\s*{re.escape(tag)}\b[^>]*\b{re.escape(attr)}=\"([^\"]+)\""
    return re.findall(pattern, text)


def summarize(model_dir: Path) -> int:
    xacro_path = model_dir / "urdf" / "bittle.xacro"
    transmission_path = model_dir / "urdf" / "bittle.trans"
    mesh_dir = model_dir / "meshes"

    if not xacro_path.is_file():
        print(f"ERROR: missing {xacro_path}", file=sys.stderr)
        print("Run: bash scripts/fetch_petoi_model.sh", file=sys.stderr)
        return 1

    text = xacro_path.read_text(encoding="utf-8")
    transmission_text = (
        transmission_path.read_text(encoding="utf-8")
        if transmission_path.is_file()
        else ""
    )
    mesh_files = sorted(mesh_dir.glob("*.stl"))
    mesh_refs = _attr_values(text, "mesh", "filename")
    link_names = _attr_values(text, "link", "name")
    joint_names = _attr_values(text, "joint", "name")
    joint_types = Counter(
        re.findall(r"<\s*joint\b[^>]*\btype=\"([^\"]+)\"", text)
    )
    movable_joints = [
        name
        for name, joint_type in re.findall(
            r"<\s*joint\b[^>]*\bname=\"([^\"]+)\"[^>]*\btype=\"([^\"]+)\"",
            text,
        )
        if joint_type in {"continuous", "revolute"}
    ]
    transmissions = _attr_values(transmission_text, "transmission", "name")

    print("Petoi Bittle ROS description summary")
    print(f"  model_dir      : {model_dir}")
    print(f"  xacro          : {xacro_path}")
    print(f"  links          : {len(link_names)}")
    print(f"  joints         : {len(joint_names)}")
    print(
        "  joint types    : "
        + ", ".join(f"{key}={value}" for key, value in sorted(joint_types.items()))
    )
    print(f"  movable joints : {len(movable_joints)}")
    print(f"  inertial tags  : {_count_tags(text, 'inertial')}")
    print(f"  mass tags      : {_count_tags(text, 'mass')}")
    print(f"  inertia tags   : {_count_tags(text, 'inertia')}")
    print(f"  mesh refs      : {len(mesh_refs)}")
    print(f"  STL files      : {len(mesh_files)}")
    print(f"  transmissions  : {len(transmissions)}")

    if mesh_refs:
        missing = []
        for ref in mesh_refs:
            name = ref.rsplit("/", 1)[-1]
            if not (mesh_dir / name).is_file():
                missing.append(ref)
        print(f"  missing meshes : {len(missing)}")
        if missing:
            for ref in missing[:10]:
                print(f"    - {ref}")

    if movable_joints:
        print("  movable names  : " + ", ".join(movable_joints))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Path to Petoi bittle_description directory.",
    )
    args = parser.parse_args()
    return summarize(args.model_dir)


if __name__ == "__main__":
    raise SystemExit(main())
