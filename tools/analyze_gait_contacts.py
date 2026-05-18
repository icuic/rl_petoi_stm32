#!/usr/bin/env python3
"""Analyze foot contact, clearance, slip, and body attitude for a rollout."""

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
import mujoco
import numpy as np
import yaml
from stable_baselines3 import PPO

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sim.envs import SimpleQuadrupedEnv


DEFAULT_MODEL = (
    "training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/"
    "ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip"
)

LEG_GEOMS = {
    "right_front": "shank_rf_1_collision_0",
    "right_rear": "shank_rr_1_collision_0",
    "left_front": "shank_lf_1_collision_0",
    "left_rear": "shank_lr_1_collision_0",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml"),
    )
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--episodes",
        type=int,
        default=1,
        help="Number of deterministic rollouts to analyze. Seeds increment from --seed or the config seed.",
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="Comma-separated rollout seeds. Overrides --episodes when provided.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/reports/gait_contact_analysis"))
    parser.add_argument("--prefix", default="petoi_bittle_v0_deployable_v0_10k")
    parser.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--contact-height-threshold",
        type=float,
        default=0.012,
        help="Fallback contact threshold for shank geom center height above the floor.",
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


def quat_to_roll_pitch(quat: np.ndarray) -> tuple[float, float]:
    w, x, y, z = quat
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)
    sinp = 2.0 * (w * y - z * x)
    pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))
    return float(roll), float(pitch)


def geom_id(model: mujoco.MjModel, name: str) -> int:
    idx = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
    if idx < 0:
        raise ValueError(f"Geom not found: {name}")
    return int(idx)


def contact_by_leg(env: SimpleQuadrupedEnv, leg_geom_ids: dict[str, int], floor_id: int, heights: dict[str, float], threshold: float) -> dict[str, bool]:
    contacts = {leg: False for leg in leg_geom_ids}
    for contact_idx in range(env.data.ncon):
        contact = env.data.contact[contact_idx]
        pair = {int(contact.geom1), int(contact.geom2)}
        if floor_id not in pair:
            continue
        for leg, gid in leg_geom_ids.items():
            if gid in pair:
                contacts[leg] = True

    for leg, height in heights.items():
        contacts[leg] = contacts[leg] or height <= threshold
    return contacts


def summarize_leg(heights: np.ndarray, contacts: np.ndarray, slip_speeds: np.ndarray) -> dict[str, float]:
    contact_mask = contacts > 0.5
    swing_mask = ~contact_mask
    contact_slip = slip_speeds[contact_mask] if np.any(contact_mask) else np.asarray([], dtype=np.float64)
    swing_heights = heights[swing_mask] if np.any(swing_mask) else np.asarray([], dtype=np.float64)
    return {
        "contact_duty_factor": float(np.mean(contacts)),
        "height_min_m": float(np.min(heights)),
        "height_mean_m": float(np.mean(heights)),
        "height_max_m": float(np.max(heights)),
        "swing_height_mean_m": float(np.mean(swing_heights)) if swing_heights.size else float("nan"),
        "contact_slip_speed_mean_m_s": float(np.mean(contact_slip)) if contact_slip.size else 0.0,
        "contact_slip_speed_p95_m_s": float(np.percentile(contact_slip, 95)) if contact_slip.size else 0.0,
    }


def summarize_front_rear(leg_summary: dict[str, dict[str, float]]) -> dict[str, float]:
    front_legs = ("right_front", "left_front")
    rear_legs = ("right_rear", "left_rear")
    front_duty = np.asarray([leg_summary[leg]["contact_duty_factor"] for leg in front_legs], dtype=np.float64)
    rear_duty = np.asarray([leg_summary[leg]["contact_duty_factor"] for leg in rear_legs], dtype=np.float64)
    front_slip = np.asarray([leg_summary[leg]["contact_slip_speed_mean_m_s"] for leg in front_legs], dtype=np.float64)
    rear_slip = np.asarray([leg_summary[leg]["contact_slip_speed_mean_m_s"] for leg in rear_legs], dtype=np.float64)
    front_slip_mean = float(np.mean(front_slip))
    rear_slip_mean = float(np.mean(rear_slip))
    return {
        "front_contact_duty_factor_mean": float(np.mean(front_duty)),
        "rear_contact_duty_factor_mean": float(np.mean(rear_duty)),
        "front_contact_slip_speed_mean_m_s": front_slip_mean,
        "rear_contact_slip_speed_mean_m_s": rear_slip_mean,
        "rear_to_front_contact_slip_ratio": rear_slip_mean / front_slip_mean if front_slip_mean > 0.0 else float("inf"),
    }


def parse_seed_list(seed_arg: str | None, base_seed: int, episodes: int) -> list[int]:
    if seed_arg:
        seeds = [int(value.strip()) for value in seed_arg.split(",") if value.strip()]
        if not seeds:
            raise ValueError("--seeds must contain at least one integer seed")
        return seeds
    if episodes < 1:
        raise ValueError("--episodes must be >= 1")
    return [base_seed + offset for offset in range(episodes)]


def mean_std(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {"mean": float(np.mean(array)), "std": float(np.std(array))}


def aggregate_rollouts(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    scalar_paths = {
        "reward": ("reward",),
        "distance_x": ("distance_x",),
        "contact_duty_factor_mean": ("aggregate", "contact_duty_factor_mean"),
        "contact_duty_factor_std": ("aggregate", "contact_duty_factor_std"),
        "contact_slip_speed_mean_m_s": ("aggregate", "contact_slip_speed_mean_m_s"),
        "swing_height_mean_m": ("aggregate", "swing_height_mean_m"),
        "base_height_mean_m": ("aggregate", "base_height_mean_m"),
        "base_roll_abs_mean_rad": ("aggregate", "base_roll_abs_mean_rad"),
        "base_pitch_abs_mean_rad": ("aggregate", "base_pitch_abs_mean_rad"),
        "front_contact_duty_factor_mean": ("front_rear", "front_contact_duty_factor_mean"),
        "rear_contact_duty_factor_mean": ("front_rear", "rear_contact_duty_factor_mean"),
        "front_contact_slip_speed_mean_m_s": ("front_rear", "front_contact_slip_speed_mean_m_s"),
        "rear_contact_slip_speed_mean_m_s": ("front_rear", "rear_contact_slip_speed_mean_m_s"),
        "rear_to_front_contact_slip_ratio": ("front_rear", "rear_to_front_contact_slip_ratio"),
    }

    aggregate: dict[str, Any] = {
        "episodes": len(summaries),
        "seeds": [int(summary["seed"]) for summary in summaries],
        "metrics": {},
        "per_leg": {},
        "termination_reasons": {},
    }
    for summary in summaries:
        reason = str(summary["termination_reason"])
        aggregate["termination_reasons"][reason] = aggregate["termination_reasons"].get(reason, 0) + 1

    for name, path in scalar_paths.items():
        values = []
        for summary in summaries:
            value: Any = summary
            for key in path:
                value = value[key]
            values.append(float(value))
        aggregate["metrics"][name] = mean_std(values)

    for leg in LEG_GEOMS:
        aggregate["per_leg"][leg] = {}
        for metric in (
            "contact_duty_factor",
            "swing_height_mean_m",
            "contact_slip_speed_mean_m_s",
            "contact_slip_speed_p95_m_s",
        ):
            aggregate["per_leg"][leg][metric] = mean_std([float(summary["legs"][leg][metric]) for summary in summaries])

    return aggregate


def run_rollout(
    args: argparse.Namespace,
    env_config: dict[str, Any],
    model: PPO,
    seed: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    env = make_env(env_config)
    obs, _ = env.reset(seed=seed)

    floor_id = geom_id(env.model, "floor")
    leg_geom_ids = {leg: geom_id(env.model, geom_name) for leg, geom_name in LEG_GEOMS.items()}
    dt = float(env.model.opt.timestep * env.frame_skip)

    leg_positions: dict[str, list[np.ndarray]] = {leg: [] for leg in leg_geom_ids}
    leg_heights: dict[str, list[float]] = {leg: [] for leg in leg_geom_ids}
    leg_contacts: dict[str, list[float]] = {leg: [] for leg in leg_geom_ids}
    base_roll: list[float] = []
    base_pitch: list[float] = []
    base_height: list[float] = []
    x_positions: list[float] = []
    rewards: list[float] = []
    termination_reason = "unknown"

    for _ in range(args.steps):
        heights = {}
        for leg, gid in leg_geom_ids.items():
            pos = env.data.geom_xpos[gid].copy()
            leg_positions[leg].append(pos)
            heights[leg] = float(pos[2])
            leg_heights[leg].append(heights[leg])

        contacts = contact_by_leg(env, leg_geom_ids, floor_id, heights, args.contact_height_threshold)
        for leg, value in contacts.items():
            leg_contacts[leg].append(1.0 if value else 0.0)

        roll, pitch = quat_to_roll_pitch(env.data.qpos[3:7])
        base_roll.append(roll)
        base_pitch.append(pitch)
        base_height.append(float(env.data.qpos[2]))
        x_positions.append(float(env.data.qpos[0]))

        action, _ = model.predict(obs, deterministic=args.deterministic)
        obs, reward, terminated, truncated, info = env.step(action)
        rewards.append(float(reward))
        termination_reason = str(info.get("termination_reason", "unknown"))
        if terminated or truncated:
            break

    final_x = float(env.data.qpos[0])
    env.close()

    height_arrays = {leg: np.asarray(values, dtype=np.float64) for leg, values in leg_heights.items()}
    contact_arrays = {leg: np.asarray(values, dtype=np.float64) for leg, values in leg_contacts.items()}
    position_arrays = {leg: np.asarray(values, dtype=np.float64) for leg, values in leg_positions.items()}
    slip_arrays: dict[str, np.ndarray] = {}
    for leg, positions in position_arrays.items():
        if len(positions) < 2:
            slip_arrays[leg] = np.zeros(len(positions), dtype=np.float64)
            continue
        xy_speed = np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1) / dt
        slip_arrays[leg] = np.concatenate([[0.0], xy_speed])

    roll_array = np.asarray(base_roll, dtype=np.float64)
    pitch_array = np.asarray(base_pitch, dtype=np.float64)
    height_array = np.asarray(base_height, dtype=np.float64)
    x_array = np.asarray(x_positions, dtype=np.float64)

    leg_summary = {
        leg: summarize_leg(height_arrays[leg], contact_arrays[leg], slip_arrays[leg])
        for leg in leg_geom_ids
    }
    contact_duties = np.asarray([leg_summary[leg]["contact_duty_factor"] for leg in leg_summary], dtype=np.float64)
    contact_slips = np.asarray([leg_summary[leg]["contact_slip_speed_mean_m_s"] for leg in leg_summary], dtype=np.float64)
    swing_heights = np.asarray([leg_summary[leg]["swing_height_mean_m"] for leg in leg_summary], dtype=np.float64)

    summary: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "model": str(args.model),
        "seed": seed,
        "deterministic": args.deterministic,
        "steps": int(len(rewards)),
        "reward": float(np.sum(rewards)),
        "distance_x": float(final_x - x_array[0]) if len(x_array) else 0.0,
        "termination_reason": termination_reason,
        "contact_height_threshold_m": args.contact_height_threshold,
        "leg_geoms": LEG_GEOMS,
        "legs": leg_summary,
        "front_rear": summarize_front_rear(leg_summary),
        "aggregate": {
            "contact_duty_factor_mean": float(np.mean(contact_duties)),
            "contact_duty_factor_std": float(np.std(contact_duties)),
            "contact_slip_speed_mean_m_s": float(np.mean(contact_slips)),
            "swing_height_mean_m": float(np.nanmean(swing_heights)),
            "base_height_mean_m": float(np.mean(height_array)),
            "base_height_std_m": float(np.std(height_array)),
            "base_roll_abs_mean_rad": float(np.mean(np.abs(roll_array))),
            "base_pitch_abs_mean_rad": float(np.mean(np.abs(pitch_array))),
            "base_roll_abs_max_rad": float(np.max(np.abs(roll_array))),
            "base_pitch_abs_max_rad": float(np.max(np.abs(pitch_array))),
        },
        "diagnostics": {
            "note": "High contact slip with low swing clearance suggests dragging or sliding instead of clean stepping.",
        },
    }
    return summary, height_arrays, contact_arrays, slip_arrays, roll_array, pitch_array, np.asarray(rewards, dtype=np.float64)


def plot_leg_series(x: np.ndarray, series: dict[str, np.ndarray], title: str, ylabel: str, output: Path) -> None:
    fig, axis = plt.subplots(figsize=(12, 5))
    for leg, values in series.items():
        axis.plot(x, values, label=leg, linewidth=1.1)
    axis.set_title(title)
    axis.set_xlabel("step")
    axis.set_ylabel(ylabel)
    axis.grid(True, alpha=0.3)
    axis.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_contact_raster(x: np.ndarray, contacts: dict[str, np.ndarray], output: Path) -> None:
    fig, axis = plt.subplots(figsize=(12, 4))
    labels = list(contacts)
    for row, leg in enumerate(labels):
        active = contacts[leg] > 0.5
        axis.fill_between(x, row, row + 0.8, where=active, step="pre", alpha=0.7)
    axis.set_yticks(np.arange(len(labels)) + 0.4)
    axis.set_yticklabels(labels)
    axis.set_xlabel("step")
    axis.set_title("Foot Contact Raster")
    axis.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    base_seed = args.seed if args.seed is not None else int(config.get("seed", 0))
    seeds = parse_seed_list(args.seeds, base_seed, args.episodes)
    env_config = config.get("env", {})

    if not args.model.exists():
        raise FileNotFoundError(f"Model not found: {args.model}")

    model = PPO.load(str(args.model), env=None, device="cpu")
    rollout_results = [run_rollout(args, env_config, model, seed) for seed in seeds]
    summaries = [result[0] for result in rollout_results]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / f"{args.prefix}_contact_summary.json"
    summary: dict[str, Any]
    if len(summaries) == 1:
        summary = summaries[0]
    else:
        summary = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": str(args.config),
            "model": str(args.model),
            "deterministic": args.deterministic,
            "steps_requested": args.steps,
            "contact_height_threshold_m": args.contact_height_threshold,
            "leg_geoms": LEG_GEOMS,
            "rollouts": summaries,
            "aggregate_across_rollouts": aggregate_rollouts(summaries),
            "diagnostics": {
                "note": "Use aggregate_across_rollouts to confirm whether contact timing and slip patterns are seed-stable.",
            },
        }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    first_summary, height_arrays, contact_arrays, slip_arrays, roll_array, pitch_array, rewards = rollout_results[0]
    plot_prefix = args.prefix if len(summaries) == 1 else f"{args.prefix}_seed{first_summary['seed']}"
    step_axis = np.arange(len(rewards))
    plot_leg_series(step_axis, height_arrays, "Shank Geom Height", "height above floor (m)", args.output_dir / f"{plot_prefix}_foot_heights.png")
    plot_leg_series(step_axis, slip_arrays, "Shank XY Speed", "speed (m/s)", args.output_dir / f"{plot_prefix}_foot_xy_speed.png")
    plot_contact_raster(step_axis, contact_arrays, args.output_dir / f"{plot_prefix}_contact_raster.png")
    plot_leg_series(
        step_axis,
        {"roll": roll_array, "pitch": pitch_array},
        "Base Roll/Pitch",
        "rad",
        args.output_dir / f"{plot_prefix}_base_attitude.png",
    )

    print(json.dumps({
        "summary": str(summary_path),
        "rollouts": len(summaries),
        "seeds": seeds,
        "first_rollout": {
            "steps": first_summary["steps"],
            "reward": first_summary["reward"],
            "distance_x": first_summary["distance_x"],
            "termination_reason": first_summary["termination_reason"],
            "aggregate": first_summary["aggregate"],
            "front_rear": first_summary["front_rear"],
        },
        "aggregate_across_rollouts": summary.get("aggregate_across_rollouts"),
        "plots": [
            str(args.output_dir / f"{plot_prefix}_foot_heights.png"),
            str(args.output_dir / f"{plot_prefix}_foot_xy_speed.png"),
            str(args.output_dir / f"{plot_prefix}_contact_raster.png"),
            str(args.output_dir / f"{plot_prefix}_base_attitude.png"),
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
