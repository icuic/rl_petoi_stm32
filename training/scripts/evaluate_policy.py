"""Evaluate a trained PPO policy and write a JSON report."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from stable_baselines3 import PPO

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sim.envs import SimpleQuadrupedEnv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("training/configs/ppo_simple_quadruped.yaml"),
        help="Path to the PPO YAML config.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Model path. Defaults to paths.final_model in the config.",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="Number of evaluation episodes. Defaults to evaluation.episodes in the config.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON report path. Defaults to evaluation.report_path in the config.",
    )
    parser.add_argument(
        "--deterministic",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use deterministic policy actions.",
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
    )


def evaluate_episode(model: PPO, env: SimpleQuadrupedEnv, deterministic: bool, seed: int) -> dict[str, Any]:
    obs, _ = env.reset(seed=seed)
    start_x = float(env.data.qpos[0])
    total_reward = 0.0
    steps = 0
    terminated = False
    truncated = False
    last_info: dict[str, Any] = {}

    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, terminated, truncated, last_info = env.step(action)
        total_reward += float(reward)
        steps += 1

    end_x = float(env.data.qpos[0])
    return {
        "seed": seed,
        "reward": total_reward,
        "steps": steps,
        "distance_x": end_x - start_x,
        "final_x": end_x,
        "terminated": terminated,
        "truncated": truncated,
        "final_phase": float(last_info.get("phase", 0.0)),
        "termination_reason": str(last_info.get("termination_reason", "unknown")),
        "final_torso_height": float(last_info.get("torso_height", np.nan)),
        "final_roll": float(last_info.get("roll", np.nan)),
        "final_pitch": float(last_info.get("pitch", np.nan)),
    }


def summarize(episodes: list[dict[str, Any]]) -> dict[str, float]:
    rewards = np.array([episode["reward"] for episode in episodes], dtype=np.float64)
    steps = np.array([episode["steps"] for episode in episodes], dtype=np.float64)
    distances = np.array([episode["distance_x"] for episode in episodes], dtype=np.float64)
    terminated = np.array([episode["terminated"] for episode in episodes], dtype=np.float64)
    final_heights = np.array([episode["final_torso_height"] for episode in episodes], dtype=np.float64)
    final_rolls = np.array([episode["final_roll"] for episode in episodes], dtype=np.float64)
    final_pitches = np.array([episode["final_pitch"] for episode in episodes], dtype=np.float64)
    reason_counts = Counter(str(episode["termination_reason"]) for episode in episodes)

    return {
        "reward_mean": float(rewards.mean()),
        "reward_std": float(rewards.std()),
        "steps_mean": float(steps.mean()),
        "distance_x_mean": float(distances.mean()),
        "distance_x_std": float(distances.std()),
        "fall_rate": float(terminated.mean()),
        "final_torso_height_mean": float(final_heights.mean()),
        "final_roll_abs_mean": float(np.abs(final_rolls).mean()),
        "final_pitch_abs_mean": float(np.abs(final_pitches).mean()),
        "termination_reason_counts": dict(sorted(reason_counts.items())),
    }


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    seed = int(config.get("seed", 0))
    env_config = config.get("env", {})
    paths_config = config.get("paths", {})
    eval_config = config.get("evaluation", {})

    model_path = args.model or Path(paths_config.get("final_model", "training/checkpoints/ppo_simple_quadruped/final_model.zip"))
    report_path = args.output or Path(eval_config.get("report_path", "experiments/reports/simple_quadruped_eval.json"))
    episodes_count = args.episodes or int(eval_config.get("episodes", 5))
    deterministic = args.deterministic
    if deterministic is None:
        deterministic = bool(eval_config.get("deterministic", True))

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    env = make_env(env_config)
    model = PPO.load(str(model_path), env=None, device=config.get("device", "auto"))

    episodes = [
        evaluate_episode(model=model, env=env, deterministic=deterministic, seed=seed + index)
        for index in range(episodes_count)
    ]
    env.close()

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "model": str(model_path),
        "deterministic": deterministic,
        "episodes": episodes,
        "summary": summarize(episodes),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(json.dumps(report["summary"], indent=2))
    print(f"Saved evaluation report to {report_path}")


if __name__ == "__main__":
    main()
