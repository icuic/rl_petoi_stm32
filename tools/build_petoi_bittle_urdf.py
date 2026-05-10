#!/usr/bin/env python3
"""Expand the fetched Petoi Bittle Xacro into a plain URDF.

The upstream file only uses simple includes, so this script intentionally keeps
the expansion narrow instead of requiring a full ROS/xacro installation.
"""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_NS = "http://www.ros.org/wiki/xacro"
ET.register_namespace("xacro", XACRO_NS)

DEFAULT_MODEL_DIR = Path(
    "third_party/petoi/ros_opencat/"
    "petoi_ROS_model_docs/bittle_ros/bittle_description"
)
DEFAULT_OUTPUT = Path("build/petoi_bittle/robot.urdf")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_robot_children(path: Path) -> list[ET.Element]:
    tree = ET.parse(path)
    root = tree.getroot()
    if _local_name(root.tag) != "robot":
        raise ValueError(f"{path} root is not <robot>")
    return [copy.deepcopy(child) for child in list(root)]


def _resolve_include(filename: str, model_dir: Path) -> Path:
    prefix = "$(find bittle_description)/"
    if filename.startswith(prefix):
        return model_dir / filename[len(prefix) :]
    path = Path(filename)
    if path.is_absolute():
        return path
    return model_dir / path


def _rewrite_mesh_paths(
    root: ET.Element,
    model_dir: Path,
    output_dir: Path,
    mode: str,
    copy_meshes: bool,
) -> int:
    package_prefix = "package://bittle_description/"
    copied = set()
    for mesh in root.iter("mesh"):
        filename = mesh.attrib.get("filename")
        if not filename or not filename.startswith(package_prefix):
            continue

        rel = filename[len(package_prefix) :]
        mesh_path = model_dir / rel
        if not mesh_path.is_file():
            raise FileNotFoundError(f"missing mesh {mesh_path}")

        if mode == "absolute":
            mesh.attrib["filename"] = str(mesh_path.resolve())
        elif mode == "relative":
            mesh.attrib["filename"] = rel
        elif mode == "basename":
            mesh.attrib["filename"] = mesh_path.name
        elif mode == "package":
            mesh.attrib["filename"] = filename
        else:
            raise ValueError(f"unknown mesh path mode: {mode}")

        if copy_meshes and mesh_path.name not in copied:
            shutil.copy2(mesh_path, output_dir / mesh_path.name)
            copied.add(mesh_path.name)

    return len(copied)


def _sanitize_for_mujoco(root: ET.Element, min_inertia: float) -> int:
    changed = 0
    for inertia in root.iter("inertia"):
        for attr in ("ixx", "iyy", "izz"):
            value = float(inertia.attrib.get(attr, "0"))
            if value < min_inertia:
                inertia.attrib[attr] = f"{min_inertia:g}"
                changed += 1
    return changed


def _name_visuals_and_collisions(root: ET.Element) -> int:
    changed = 0
    for link in root.iter("link"):
        link_name = link.attrib.get("name", "link")
        counts = {"visual": 0, "collision": 0}
        for child in list(link):
            tag = _local_name(child.tag)
            if tag not in counts:
                continue
            if not child.attrib.get("name"):
                child.attrib["name"] = f"{link_name}_{tag}_{counts[tag]}"
                changed += 1
            counts[tag] += 1
    return changed


def expand(
    model_dir: Path,
    output: Path,
    mesh_paths: str,
    copy_meshes: bool,
    include_ros_tags: bool,
    mujoco_sanitize: bool,
    min_inertia: float,
) -> tuple[Path, int, int, int]:
    xacro_path = model_dir / "urdf" / "bittle.xacro"
    if not xacro_path.is_file():
        raise FileNotFoundError(
            f"missing {xacro_path}; run: bash scripts/fetch_petoi_model.sh"
        )

    tree = ET.parse(xacro_path)
    root = tree.getroot()
    expanded = ET.Element("robot", {"name": root.attrib.get("name", "bittle")})

    include_tag = f"{{{XACRO_NS}}}include"
    skipped = {"bittle.gazebo", "bittle.trans"}
    for child in list(root):
        if child.tag == include_tag:
            include_path = _resolve_include(child.attrib["filename"], model_dir)
            if not include_ros_tags and include_path.name in skipped:
                continue
            expanded.extend(_read_robot_children(include_path))
            continue
        expanded.append(copy.deepcopy(child))

    output.parent.mkdir(parents=True, exist_ok=True)
    copied_meshes = _rewrite_mesh_paths(
        expanded,
        model_dir,
        output.parent,
        mesh_paths,
        copy_meshes,
    )
    named_visuals_collisions = _name_visuals_and_collisions(expanded)
    changed_inertias = (
        _sanitize_for_mujoco(expanded, min_inertia) if mujoco_sanitize else 0
    )

    ET.indent(expanded, space="  ")
    ET.ElementTree(expanded).write(
        output,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    )
    return output, changed_inertias, copied_meshes, named_visuals_collisions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--mesh-paths",
        choices=("absolute", "relative", "basename", "package"),
        default="absolute",
    )
    parser.add_argument(
        "--copy-meshes",
        action="store_true",
        help="Copy referenced STL files next to the generated URDF.",
    )
    parser.add_argument(
        "--include-ros-tags",
        action="store_true",
        help="Include Gazebo and ROS transmission tags in the generated URDF.",
    )
    parser.add_argument(
        "--mujoco-sanitize",
        action="store_true",
        help="Raise zero diagonal inertias to a small positive value.",
    )
    parser.add_argument("--min-inertia", type=float, default=1e-9)
    args = parser.parse_args()

    try:
        output, changed_inertias, copied_meshes, named_visuals_collisions = expand(
            args.model_dir,
            args.output,
            args.mesh_paths,
            args.copy_meshes,
            args.include_ros_tags,
            args.mujoco_sanitize,
            args.min_inertia,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    print(f"mesh_paths={args.mesh_paths}")
    print(f"copied_meshes={copied_meshes}")
    print(f"named_visuals_collisions={named_visuals_collisions}")
    print(f"mujoco_sanitize={args.mujoco_sanitize}")
    print(f"changed_inertias={changed_inertias}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
