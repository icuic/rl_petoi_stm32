#!/usr/bin/env python3
"""Search simple stand poses for the generated Petoi Bittle MJCF."""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class TrialResult:
    shoulder: float
    knee: float
    score: float
    final_z: float
    min_z: float
    max_tilt: float
    final_tilt: float
    xy_drift: float
    max_abs_qvel: float
    finite: bool


def _parse_values(text: str) -> list[float]:
    return [float(value) for value in text.split(",") if value.strip()]


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


def _is_finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _leg_pose(shoulder: float, knee: float):
    return [shoulder, knee, shoulder, knee, shoulder, knee, shoulder, knee]


def _set_joint_qpos(mujoco, model, data, joint_name: str, value: float) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise ValueError(f"missing joint {joint_name}")
    qpos_addr = model.jnt_qposadr[joint_id]
    data.qpos[qpos_addr] = value


def evaluate_pose(mujoco, np, model, shoulder: float, knee: float, steps: int, root_z: float) -> TrialResult:
    data = mujoco.MjData(model)
    pose = _leg_pose(shoulder, knee)

    data.qpos[0:3] = [0.0, 0.0, root_z]
    data.qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
    for joint_name, value in zip(LEG_JOINTS, pose):
        _set_joint_qpos(mujoco, model, data, joint_name, value)
    data.ctrl[:] = pose
    mujoco.mj_forward(model, data)

    min_z = float(data.qpos[2])
    max_tilt = 0.0
    max_abs_qvel = 0.0
    start_xy = np.array(data.qpos[0:2], dtype=float)
    finite = True

    for _ in range(steps):
        mujoco.mj_step(model, data)
        if not _is_finite(data.qpos) or not _is_finite(data.qvel):
            finite = False
            break
        roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
        max_tilt = max(max_tilt, abs(roll), abs(pitch))
        min_z = min(min_z, float(data.qpos[2]))
        max_abs_qvel = max(max_abs_qvel, float(np.max(np.abs(data.qvel))))

    final_z = float(data.qpos[2])
    roll, pitch = _quat_to_roll_pitch(data.qpos[3:7])
    final_tilt = max(abs(roll), abs(pitch))
    xy_drift = float(np.linalg.norm(np.array(data.qpos[0:2], dtype=float) - start_xy))

    # Higher is better. Strong penalties make this a stability ranking, not a
    # height contest.
    score = (
        final_z
        + 0.5 * min_z
        - 0.35 * max_tilt
        - 0.15 * final_tilt
        - 0.2 * xy_drift
        - 0.01 * max_abs_qvel
    )
    if not finite:
        score -= 1000.0

    return TrialResult(
        shoulder=shoulder,
        knee=knee,
        score=score,
        final_z=final_z,
        min_z=min_z,
        max_tilt=max_tilt,
        final_tilt=final_tilt,
        xy_drift=xy_drift,
        max_abs_qvel=max_abs_qvel,
        finite=finite,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path, nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("--steps", type=int, default=800)
    parser.add_argument("--root-z", type=float, default=0.18)
    parser.add_argument(
        "--shoulders",
        default="-0.6,-0.4,-0.2,0,0.2,0.4,0.6",
        help="Comma-separated shoulder joint targets in radians.",
    )
    parser.add_argument(
        "--knees",
        default="-1.0,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1.0",
        help="Comma-separated knee joint targets in radians.",
    )
    parser.add_argument("--top", type=int, default=10)
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

    if model.nu != len(LEG_JOINTS):
        print(f"ERROR: expected {len(LEG_JOINTS)} actuators, got {model.nu}", file=sys.stderr)
        return 1

    shoulders = _parse_values(args.shoulders)
    knees = _parse_values(args.knees)
    results = [
        evaluate_pose(mujoco, np, model, shoulder, knee, args.steps, args.root_z)
        for shoulder, knee in itertools.product(shoulders, knees)
    ]
    results.sort(key=lambda item: item.score, reverse=True)

    print(f"Evaluated {len(results)} stand pose candidates")
    print("rank shoulder knee score final_z min_z max_tilt final_tilt xy_drift max_abs_qvel finite")
    for rank, result in enumerate(results[: args.top], start=1):
        print(
            f"{rank:>4} "
            f"{result.shoulder:>8.3f} "
            f"{result.knee:>6.3f} "
            f"{result.score:>8.4f} "
            f"{result.final_z:>7.4f} "
            f"{result.min_z:>7.4f} "
            f"{result.max_tilt:>8.4f} "
            f"{result.final_tilt:>10.4f} "
            f"{result.xy_drift:>8.4f} "
            f"{result.max_abs_qvel:>12.4f} "
            f"{result.finite}"
        )

    best = results[0]
    pose = _leg_pose(best.shoulder, best.knee)
    print("best_pose=" + ",".join(f"{value:.6f}" for value in pose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
