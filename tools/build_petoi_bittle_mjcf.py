#!/usr/bin/env python3
"""Generate a trainable MuJoCo MJCF from the generated Petoi Bittle URDF."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_URDF = Path("build/petoi_bittle/robot.urdf")
DEFAULT_OUTPUT = Path("build/petoi_bittle/petoi_bittle_v0.xml")

LEG_JOINTS = (
    "shrfs_joint",
    "shrft_joint",
    "shrrs_joint",
    "shrrt_joint",
    "shlfs_joint",
    "shlft_joint",
    "shlrs_joint",
    "shlrt_joint",
)
NECK_JOINT = "neck_joint"


def _load_and_save_urdf_as_mjcf(urdf: Path, temp_mjcf: Path) -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_path(str(urdf))
    mujoco.mj_saveLastXML(str(temp_mjcf), model)


def _set_or_insert(root: ET.Element, tag: str, attrs: dict[str, str], index: int) -> ET.Element:
    elem = root.find(tag)
    if elem is None:
        elem = ET.Element(tag)
        root.insert(index, elem)
    elem.attrib.update(attrs)
    return elem


def _wrap_worldbody(worldbody: ET.Element, base_mass: float) -> None:
    original_children = list(worldbody)
    for child in original_children:
        worldbody.remove(child)

    ET.SubElement(
        worldbody,
        "geom",
        {
            "name": "floor",
            "type": "plane",
            "size": "2 2 0.02",
            "rgba": "0.72 0.72 0.72 1",
            "friction": "0.9 0.02 0.001",
        },
    )
    ET.SubElement(
        worldbody,
        "light",
        {
            "name": "key_light",
            "pos": "0 -1.5 1.5",
            "dir": "0 1 -1",
            "diffuse": "0.8 0.8 0.8",
        },
    )
    base = ET.SubElement(
        worldbody,
        "body",
        {
            "name": "bittle_base",
            "pos": "0 0 0.16",
        },
    )
    ET.SubElement(base, "freejoint", {"name": "root"})
    ET.SubElement(
        base,
        "inertial",
        {
            "pos": "0 0 0",
            "mass": f"{base_mass:g}",
            "diaginertia": "0.00016 0.00024 0.00028",
        },
    )
    for child in original_children:
        base.append(child)


def _configure_joints(root: ET.Element) -> None:
    for joint in root.iter("joint"):
        name = joint.attrib.get("name")
        if name in LEG_JOINTS:
            joint.attrib.update(
                {
                    "limited": "true",
                    "range": "-2.61799 2.61799",
                    "damping": "0.02",
                    "armature": "0.001",
                    "frictionloss": "0.001",
                }
            )
        elif name == NECK_JOINT:
            joint.attrib.update(
                {
                    "limited": "true",
                    "range": "-1.5708 1.5708",
                    "damping": "0.02",
                    "armature": "0.001",
                    "frictionloss": "0.001",
                }
            )


def _add_actuators(root: ET.Element, kp: float, force: float, ctrl: float) -> None:
    existing = root.find("actuator")
    if existing is not None:
        root.remove(existing)

    actuator = ET.SubElement(root, "actuator")
    for joint_name in LEG_JOINTS:
        ET.SubElement(
            actuator,
            "position",
            {
                "name": f"{joint_name}_pos",
                "joint": joint_name,
                "kp": f"{kp:g}",
                "ctrlrange": f"{-ctrl:g} {ctrl:g}",
                "forcerange": f"{-force:g} {force:g}",
            },
        )


def build_mjcf(
    urdf: Path,
    output: Path,
    base_mass: float,
    kp: float,
    force: float,
    ctrl: float,
) -> Path:
    if not urdf.is_file():
        raise FileNotFoundError(f"missing {urdf}; run: bash scripts/build_petoi_urdf.sh")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_mjcf = output.with_suffix(".imported.xml")
    _load_and_save_urdf_as_mjcf(urdf, temp_mjcf)

    tree = ET.parse(temp_mjcf)
    root = tree.getroot()
    root.attrib["model"] = "petoi_bittle_v0"

    _set_or_insert(
        root,
        "compiler",
        {"angle": "radian", "coordinate": "local", "autolimits": "true"},
        0,
    )
    _set_or_insert(
        root,
        "option",
        {"timestep": "0.002", "integrator": "RK4", "gravity": "0 0 -9.81"},
        1,
    )
    _set_or_insert(
        root,
        "default",
        {},
        2,
    )

    worldbody = root.find("worldbody")
    if worldbody is None:
        raise ValueError("imported MJCF has no worldbody")

    _wrap_worldbody(worldbody, base_mass)
    _configure_joints(root)
    _add_actuators(root, kp, force, ctrl)

    ET.indent(root, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=False, short_empty_elements=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=Path, default=DEFAULT_URDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-mass", type=float, default=0.18)
    parser.add_argument("--kp", type=float, default=2.5)
    parser.add_argument("--force", type=float, default=1.2)
    parser.add_argument("--ctrl", type=float, default=1.2)
    args = parser.parse_args()

    try:
        output = build_mjcf(args.urdf, args.output, args.base_mass, args.kp, args.force, args.ctrl)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    print(f"leg_actuators={len(LEG_JOINTS)}")
    print(f"base_mass={args.base_mass:g}")
    print(f"kp={args.kp:g}")
    print(f"force={args.force:g}")
    print(f"ctrl={args.ctrl:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
