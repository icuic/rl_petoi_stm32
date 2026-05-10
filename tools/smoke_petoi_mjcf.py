#!/usr/bin/env python3
"""Basic load and physics smoke test for the generated Petoi Bittle MJCF."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


DEFAULT_MODEL = Path("build/petoi_bittle/petoi_bittle_v0.xml")
DEFAULT_STAND_POSE = (0.2, 1.4, 0.2, 1.4, 0.2, 1.4, 0.2, 1.4)
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


def _finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _parse_pose(text: str) -> list[float]:
    values = [float(value) for value in text.split(",") if value.strip()]
    if len(values) != len(LEG_JOINTS):
        raise ValueError(f"expected {len(LEG_JOINTS)} pose values, got {len(values)}")
    return values


def _set_joint_qpos(mujoco, model, data, joint_name: str, value: float) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise ValueError(f"missing joint {joint_name}")
    data.qpos[model.jnt_qposadr[joint_id]] = value


def _quat_to_roll_pitch(quat) -> tuple[float, float]:
    w, x, y, z = [float(v) for v in quat]
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)
    return roll, pitch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path, nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--root-z", type=float, default=0.18)
    parser.add_argument(
        "--stand-pose",
        default=",".join(f"{value:g}" for value in DEFAULT_STAND_POSE),
        help="Comma-separated 8D leg joint target used for the smoke test.",
    )
    args = parser.parse_args()

    try:
        import mujoco
        import numpy as np
    except ImportError as exc:
        print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
        return 1

    try:
        model = mujoco.MjModel.from_xml_path(str(args.model))
    except Exception as exc:
        print(f"ERROR: failed to load {args.model}: {exc}", file=sys.stderr)
        return 1

    data = mujoco.MjData(model)
    actuator_names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, idx)
        for idx in range(model.nu)
    ]
    joint_names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, idx)
        for idx in range(model.njnt)
    ]
    missing_joints = [name for name in LEG_JOINTS if name not in joint_names]
    missing_actuators = [f"{name}_pos" for name in LEG_JOINTS if f"{name}_pos" not in actuator_names]

    if missing_joints or missing_actuators:
        print(f"ERROR: missing_joints={missing_joints}", file=sys.stderr)
        print(f"ERROR: missing_actuators={missing_actuators}", file=sys.stderr)
        return 1

    try:
        stand_pose = np.array(_parse_pose(args.stand_pose), dtype=float)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    data.qpos[0:3] = [0.0, 0.0, args.root_z]
    data.qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
    for joint_name, value in zip(LEG_JOINTS, stand_pose):
        _set_joint_qpos(mujoco, model, data, joint_name, value)
    data.ctrl[:] = stand_pose
    mujoco.mj_forward(model, data)

    min_z = float("inf")
    max_abs_qvel = 0.0
    max_tilt = 0.0
    start_xy = np.array(data.qpos[0:2], dtype=float)
    for _ in range(args.steps):
        mujoco.mj_step(model, data)
        min_z = min(min_z, float(data.qpos[2]))
        max_abs_qvel = max(max_abs_qvel, float(np.max(np.abs(data.qvel))))
        roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
        max_tilt = max(max_tilt, abs(roll), abs(pitch))
        if not _finite(data.qpos) or not _finite(data.qvel):
            print("ERROR: simulation produced non-finite state", file=sys.stderr)
            return 1
    roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
    xy_drift = float(np.linalg.norm(np.array(data.qpos[0:2], dtype=float) - start_xy))

    print(f"Loaded {args.model}")
    print(f"  nq          : {model.nq}")
    print(f"  nv          : {model.nv}")
    print(f"  nu          : {model.nu}")
    print(f"  nbody       : {model.nbody}")
    print(f"  njnt        : {model.njnt}")
    print(f"  ngeom       : {model.ngeom}")
    print(f"  nmesh       : {model.nmesh}")
    print(f"  actuators   : {', '.join(actuator_names)}")
    print("  stand_pose  : " + ",".join(f"{value:g}" for value in stand_pose))
    print(f"  final_z     : {float(data.qpos[2]):.6f}")
    print(f"  min_z       : {min_z:.6f}")
    print(f"  final_roll  : {roll:.6f}")
    print(f"  final_pitch : {pitch:.6f}")
    print(f"  max_tilt    : {max_tilt:.6f}")
    print(f"  xy_drift    : {xy_drift:.6f}")
    print(f"  max_abs_qvel: {max_abs_qvel:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
