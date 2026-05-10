#!/usr/bin/env python3
"""Run an open-loop trot reference on the generated Petoi Bittle MJCF."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sim.envs.gait_reference import DEFAULT_PETOI_STAND_POSE, trot_reference


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


def _finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _set_joint_qpos(mujoco, model, data, joint_name: str, value: float) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise ValueError(f"missing joint {joint_name}")
    data.qpos[model.jnt_qposadr[joint_id]] = value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path, nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--root-z", type=float, default=0.18)
    parser.add_argument("--period-steps", type=int, default=120)
    parser.add_argument("--shoulder-amplitude", type=float, default=0.12)
    parser.add_argument("--knee-amplitude", type=float, default=0.10)
    parser.add_argument("--duty-bias", type=float, default=0.0)
    args = parser.parse_args()

    try:
        import mujoco
        import numpy as np
    except ImportError as exc:
        print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
        return 1

    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)

    actuator_names = [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, idx)
        for idx in range(model.nu)
    ]
    missing_actuators = [f"{name}_pos" for name in LEG_JOINTS if f"{name}_pos" not in actuator_names]
    if missing_actuators:
        print(f"ERROR: missing actuators: {missing_actuators}", file=sys.stderr)
        return 1

    initial_pose = trot_reference(
        phase=0.0,
        stand_pose=DEFAULT_PETOI_STAND_POSE,
        shoulder_amplitude=args.shoulder_amplitude,
        knee_amplitude=args.knee_amplitude,
        duty_bias=args.duty_bias,
    )
    data.qpos[0:3] = [0.0, 0.0, args.root_z]
    data.qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
    for joint_name, value in zip(LEG_JOINTS, initial_pose):
        _set_joint_qpos(mujoco, model, data, joint_name, float(value))
    data.ctrl[:] = initial_pose
    mujoco.mj_forward(model, data)

    start_xy = np.array(data.qpos[0:2], dtype=float)
    min_z = float(data.qpos[2])
    max_tilt = 0.0
    max_abs_qvel = 0.0
    finite = True

    for step in range(args.steps):
        phase = (step % args.period_steps) / float(args.period_steps)
        target = trot_reference(
            phase=phase,
            stand_pose=DEFAULT_PETOI_STAND_POSE,
            shoulder_amplitude=args.shoulder_amplitude,
            knee_amplitude=args.knee_amplitude,
            duty_bias=args.duty_bias,
        )
        data.ctrl[:] = target
        mujoco.mj_step(model, data)
        if not _finite(data.qpos) or not _finite(data.qvel):
            finite = False
            break
        roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
        min_z = min(min_z, float(data.qpos[2]))
        max_tilt = max(max_tilt, abs(roll), abs(pitch))
        max_abs_qvel = max(max_abs_qvel, float(np.max(np.abs(data.qvel))))

    roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
    xy = np.array(data.qpos[0:2], dtype=float)
    displacement = xy - start_xy

    print(f"Loaded {args.model}")
    print(f"  steps              : {args.steps}")
    print(f"  period_steps       : {args.period_steps}")
    print(f"  shoulder_amplitude : {args.shoulder_amplitude:.6f}")
    print(f"  knee_amplitude     : {args.knee_amplitude:.6f}")
    print(f"  duty_bias          : {args.duty_bias:.6f}")
    print(f"  finite             : {finite}")
    print(f"  distance_x         : {float(displacement[0]):.6f}")
    print(f"  distance_y         : {float(displacement[1]):.6f}")
    print(f"  final_z            : {float(data.qpos[2]):.6f}")
    print(f"  min_z              : {min_z:.6f}")
    print(f"  final_roll         : {roll:.6f}")
    print(f"  final_pitch        : {pitch:.6f}")
    print(f"  max_tilt           : {max_tilt:.6f}")
    print(f"  max_abs_qvel       : {max_abs_qvel:.6f}")
    if not finite:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
