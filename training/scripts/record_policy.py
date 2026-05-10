"""Record a trained PPO policy rollout to an MP4 file."""

from __future__ import annotations

import argparse
import os

os.environ.setdefault("MUJOCO_GL", "egl")

import sys
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
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
        "--output",
        type=Path,
        default=Path("assets/videos/simple_quadruped_rollout.mp4"),
        help="Output MP4 path.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Rollout seed. Defaults to config seed.")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum recorded steps.")
    parser.add_argument("--fps", type=int, default=50, help="Output video frame rate.")
    parser.add_argument(
        "--deterministic",
        action=argparse.BooleanOptionalAction,
        default=True,
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
        control_config=env_config.get("control", {}),
        render_mode="rgb_array",
    )


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    env_config = config.get("env", {})
    paths_config = config.get("paths", {})
    eval_config = config.get("evaluation", {})
    seed = args.seed if args.seed is not None else int(config.get("seed", 0))
    max_steps = args.max_steps or int(env_config.get("episode_steps", 1000))
    deterministic = args.deterministic

    model_path = args.model or Path(paths_config.get("final_model", "training/checkpoints/ppo_simple_quadruped/final_model.zip"))
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    env = make_env(env_config)
    model = PPO.load(str(model_path), env=None, device=config.get("device", "auto"))
    obs, _ = env.reset(seed=seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(args.output, fps=args.fps, codec="libx264", quality=8)

    total_reward = 0.0
    steps = 0
    termination_reason = "unknown"
    try:
        for _ in range(max_steps):
            frame = env.render()
            if frame is not None:
                writer.append_data(frame)

            action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += float(reward)
            steps += 1
            termination_reason = str(info.get("termination_reason", "unknown"))
            if terminated or truncated:
                break
    finally:
        writer.close()
        env.close()

    print(f"Saved rollout video to {args.output}")
    print(f"steps={steps} reward={total_reward:.3f} termination_reason={termination_reason}")
    if bool(eval_config.get("deterministic", True)) != deterministic:
        print(f"note: config evaluation.deterministic={eval_config.get('deterministic')} but recording used {deterministic}")


if __name__ == "__main__":
    main()
