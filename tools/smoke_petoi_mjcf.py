#!/usr/bin/env python3
"""Basic load and physics smoke test for the generated Petoi Bittle MJCF."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


DEFAULT_MODEL = Path("build/petoi_bittle/petoi_bittle_v0.xml")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path, nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("--steps", type=int, default=500)
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

    # Mild crouch-like neutral pose. This is not yet a calibrated stand pose.
    neutral = np.array([0.0, 0.55, 0.0, 0.55, 0.0, 0.55, 0.0, 0.55])
    data.ctrl[:] = neutral

    min_z = float("inf")
    max_abs_qvel = 0.0
    for _ in range(args.steps):
        mujoco.mj_step(model, data)
        min_z = min(min_z, float(data.qpos[2]))
        max_abs_qvel = max(max_abs_qvel, float(np.max(np.abs(data.qvel))))
        if not _finite(data.qpos) or not _finite(data.qvel):
            print("ERROR: simulation produced non-finite state", file=sys.stderr)
            return 1

    print(f"Loaded {args.model}")
    print(f"  nq          : {model.nq}")
    print(f"  nv          : {model.nv}")
    print(f"  nu          : {model.nu}")
    print(f"  nbody       : {model.nbody}")
    print(f"  njnt        : {model.njnt}")
    print(f"  ngeom       : {model.ngeom}")
    print(f"  nmesh       : {model.nmesh}")
    print(f"  actuators   : {', '.join(actuator_names)}")
    print(f"  final_z     : {float(data.qpos[2]):.6f}")
    print(f"  min_z       : {min_z:.6f}")
    print(f"  max_abs_qvel: {max_abs_qvel:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
