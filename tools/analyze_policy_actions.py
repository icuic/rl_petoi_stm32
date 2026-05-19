#!/usr/bin/env python3
"""Analyze policy residual actions and joint targets for a rollout."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"))

import matplotlib.pyplot as plt
import numpy as np
import yaml
from stable_baselines3 import PPO

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sim.envs import SimpleQuadrupedEnv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml"),
        help="PPO YAML config.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(
            "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/"
            "ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip"
        ),
        help="Policy checkpoint to analyze.",
    )
    parser.add_argument("--steps", type=int, default=1000, help="Maximum rollout steps.")
    parser.add_argument("--seed", type=int, default=None, help="Rollout seed. Defaults to config seed.")
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/reports/action_analysis"))
    parser.add_argument("--prefix", default="petoi_bittle_v0_deployable_v0_10k")
    parser.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--zero-action",
        action="store_true",
        help="Analyze the residual gait prior with zero policy residual instead of loading PPO.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return config


def make_env(env_config: dict[str, Any]) -> SimpleQuadrupedEnv:
    return SimpleQuadrupedEnv(
        model_path=env_config.get("model_path"),
        frame_skip=int(env_config.get("frame_skip", 10)),
        episode_steps=int(env_config.get("episode_steps", 1000)),
        reward_config=env_config.get("reward", {}),
        reset_config=env_config.get("reset", {}),
        control_config=env_config.get("control", {}),
        observation_config=env_config.get("observation", {}),
    )


def rms(values: np.ndarray, axis: int = 0) -> np.ndarray:
    return np.sqrt(np.mean(np.square(values), axis=axis))


def peak_to_peak(values: np.ndarray, axis: int = 0) -> np.ndarray:
    return np.ptp(values, axis=axis)


def summarize_group(name: str, indices: list[int], actions: np.ndarray, residual_rad: np.ndarray, targets: np.ndarray) -> dict[str, Any]:
    action_abs_mean = np.mean(np.abs(actions[:, indices]), axis=0)
    residual_abs_mean = np.mean(np.abs(residual_rad[:, indices]), axis=0)
    return {
        "name": name,
        "indices": indices,
        "action_abs_mean_by_joint": action_abs_mean.astype(float).tolist(),
        "action_abs_mean": float(np.mean(action_abs_mean)),
        "action_rms_by_joint": rms(actions[:, indices]).astype(float).tolist(),
        "action_rms": float(np.mean(rms(actions[:, indices]))),
        "residual_rad_abs_mean_by_joint": residual_abs_mean.astype(float).tolist(),
        "residual_rad_abs_mean": float(np.mean(residual_abs_mean)),
        "target_rad_peak_to_peak_by_joint": peak_to_peak(targets[:, indices]).astype(float).tolist(),
        "target_rad_peak_to_peak": float(np.mean(peak_to_peak(targets[:, indices]))),
    }


def plot_lines(
    x: np.ndarray,
    values: np.ndarray,
    joint_names: tuple[str, ...],
    title: str,
    ylabel: str,
    output: Path,
) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(13, 10), sharex=True)
    axes_flat = axes.flatten()
    for idx, axis in enumerate(axes_flat):
        axis.plot(x, values[:, idx], linewidth=1.2)
        axis.set_title(joint_names[idx], fontsize=9)
        axis.grid(True, alpha=0.3)
        axis.set_ylabel(ylabel)
    axes_flat[-2].set_xlabel("step")
    axes_flat[-1].set_xlabel("step")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_group_comparison(summary: dict[str, Any], output: Path) -> None:
    groups = summary["groups"]
    labels = [groups["shoulder_or_hip"]["name"], groups["knee_or_lower_leg"]["name"]]
    action_abs = [groups["shoulder_or_hip"]["action_abs_mean"], groups["knee_or_lower_leg"]["action_abs_mean"]]
    target_ptp = [groups["shoulder_or_hip"]["target_rad_peak_to_peak"], groups["knee_or_lower_leg"]["target_rad_peak_to_peak"]]
    residual_abs = [groups["shoulder_or_hip"]["residual_rad_abs_mean"], groups["knee_or_lower_leg"]["residual_rad_abs_mean"]]

    x = np.arange(len(labels))
    width = 0.25
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.bar(x - width, action_abs, width, label="|policy action| mean")
    axis.bar(x, residual_abs, width, label="|residual| mean (rad)")
    axis.bar(x + width, target_ptp, width, label="target peak-to-peak (rad)")
    axis.set_xticks(x)
    axis.set_xticklabels(labels)
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()
    axis.set_title("Shoulder/Hip vs Knee/Lower-Leg Motion")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    seed = args.seed if args.seed is not None else int(config.get("seed", 0))
    env_config = config.get("env", {})

    if not args.zero_action and not args.model.exists():
        raise FileNotFoundError(f"Model not found: {args.model}")

    env = make_env(env_config)
    model = None if args.zero_action else PPO.load(str(args.model), env=None, device="cpu")
    obs, _ = env.reset(seed=seed)

    actions: list[np.ndarray] = []
    references: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    qpos: list[np.ndarray] = []
    phases: list[float] = []
    rewards: list[float] = []
    x_positions: list[float] = []
    termination_reason = "unknown"

    for _ in range(args.steps):
        if args.zero_action:
            action = np.zeros(env.action_space.shape, dtype=env.action_space.dtype)
        else:
            if model is None:
                raise ValueError("model is required unless --zero-action is set")
            action, _ = model.predict(obs, deterministic=args.deterministic)
        action = np.asarray(action, dtype=np.float32)
        reference = env._reference_joint_targets(env.phase).copy()
        target = env._normalized_action_to_joint_targets(action).copy()
        joint_qpos = env.data.qpos[env.joint_qpos_addr].copy()

        actions.append(action.copy())
        references.append(reference)
        targets.append(target)
        qpos.append(joint_qpos)
        phases.append(float(env.phase))
        x_positions.append(float(env.data.qpos[0]))

        obs, reward, terminated, truncated, info = env.step(action)
        rewards.append(float(reward))
        termination_reason = str(info.get("termination_reason", "unknown"))
        if terminated or truncated:
            break

    final_x = float(env.data.qpos[0])
    env.close()

    actions_array = np.asarray(actions, dtype=np.float32)
    references_array = np.asarray(references, dtype=np.float32)
    targets_array = np.asarray(targets, dtype=np.float32)
    qpos_array = np.asarray(qpos, dtype=np.float32)
    residual_rad = targets_array - references_array
    x_positions_array = np.asarray(x_positions, dtype=np.float32)

    joint_names = tuple(str(name) for name in env_config.get("control", {}).get("joint_names", (f"joint_{i}" for i in range(actions_array.shape[1]))))
    shoulder_indices = [0, 2, 4, 6]
    knee_indices = [1, 3, 5, 7]

    summary: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "model": None if args.zero_action else str(args.model),
        "policy_mode": "zero_action" if args.zero_action else "ppo",
        "seed": seed,
        "deterministic": args.deterministic,
        "steps": int(actions_array.shape[0]),
        "reward": float(np.sum(rewards)),
        "termination_reason": termination_reason,
        "distance_x": float(final_x - x_positions_array[0]) if len(x_positions_array) else 0.0,
        "joint_names": list(joint_names),
        "action_scale": np.asarray(env_config.get("control", {}).get("action_scale", [0.0] * 8), dtype=np.float32).astype(float).tolist(),
        "groups": {
            "shoulder_or_hip": summarize_group("shoulder_or_hip", shoulder_indices, actions_array, residual_rad, targets_array),
            "knee_or_lower_leg": summarize_group("knee_or_lower_leg", knee_indices, actions_array, residual_rad, targets_array),
        },
        "per_joint": {},
    }

    for idx, joint_name in enumerate(joint_names):
        summary["per_joint"][joint_name] = {
            "action_abs_mean": float(np.mean(np.abs(actions_array[:, idx]))),
            "action_rms": float(rms(actions_array[:, idx], axis=0)),
            "action_peak_to_peak": float(peak_to_peak(actions_array[:, idx], axis=0)),
            "residual_rad_abs_mean": float(np.mean(np.abs(residual_rad[:, idx]))),
            "reference_rad_peak_to_peak": float(peak_to_peak(references_array[:, idx], axis=0)),
            "target_rad_peak_to_peak": float(peak_to_peak(targets_array[:, idx], axis=0)),
            "qpos_rad_peak_to_peak": float(peak_to_peak(qpos_array[:, idx], axis=0)),
        }

    hip_action = summary["groups"]["shoulder_or_hip"]["action_abs_mean"]
    knee_action = summary["groups"]["knee_or_lower_leg"]["action_abs_mean"]
    summary["diagnostics"] = {
        "knee_to_shoulder_action_abs_ratio": float(knee_action / hip_action) if hip_action > 0 else None,
        "note": "Large knee/shoulder ratios suggest the learned residual relies more on lower-leg motion.",
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / f"{args.prefix}_action_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    step_axis = np.arange(actions_array.shape[0])
    plot_lines(
        step_axis,
        actions_array,
        joint_names,
        "Policy Residual Actions",
        "normalized action",
        args.output_dir / f"{args.prefix}_actions.png",
    )
    plot_lines(
        step_axis,
        targets_array,
        joint_names,
        "Joint Targets",
        "target rad",
        args.output_dir / f"{args.prefix}_targets.png",
    )
    plot_lines(
        step_axis,
        references_array,
        joint_names,
        "Residual Trot Reference",
        "reference rad",
        args.output_dir / f"{args.prefix}_reference.png",
    )
    plot_group_comparison(summary, args.output_dir / f"{args.prefix}_group_comparison.png")

    print(json.dumps({
        "summary": str(summary_path),
        "steps": summary["steps"],
        "reward": summary["reward"],
        "distance_x": summary["distance_x"],
        "termination_reason": termination_reason,
        "knee_to_shoulder_action_abs_ratio": summary["diagnostics"]["knee_to_shoulder_action_abs_ratio"],
        "plots": [
            str(args.output_dir / f"{args.prefix}_actions.png"),
            str(args.output_dir / f"{args.prefix}_targets.png"),
            str(args.output_dir / f"{args.prefix}_reference.png"),
            str(args.output_dir / f"{args.prefix}_group_comparison.png"),
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
