"""Train a PPO baseline on the minimal quadruped environment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.utils import set_random_seed

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
        "--total-timesteps",
        type=int,
        default=None,
        help="Override total_timesteps from the config. Useful for dry-runs.",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Run SB3 env checker before training.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return config


def make_env_factory(env_config: dict[str, Any]):
    def _make_env():
        return SimpleQuadrupedEnv(
            frame_skip=int(env_config.get("frame_skip", 10)),
            episode_steps=int(env_config.get("episode_steps", 1000)),
        )

    return _make_env


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    seed = int(config.get("seed", 0))
    total_timesteps = args.total_timesteps or int(config["total_timesteps"])
    env_config = config.get("env", {})
    ppo_config = config.get("ppo", {})
    paths_config = config.get("paths", {})
    checkpoint_config = config.get("checkpoint", {})

    log_dir = Path(paths_config.get("log_dir", "training/logs/ppo_simple_quadruped"))
    checkpoint_dir = Path(paths_config.get("checkpoint_dir", "training/checkpoints/ppo_simple_quadruped"))
    final_model = Path(paths_config.get("final_model", checkpoint_dir / "final_model.zip"))
    log_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    final_model.parent.mkdir(parents=True, exist_ok=True)

    set_random_seed(seed)

    if args.check_env:
        check_env(make_env_factory(env_config)(), warn=True)

    env = make_vec_env(
        make_env_factory(env_config),
        n_envs=int(env_config.get("n_envs", 1)),
        seed=seed,
    )

    callback = CheckpointCallback(
        save_freq=max(1, int(checkpoint_config.get("save_freq", 2000))),
        save_path=str(checkpoint_dir),
        name_prefix=str(checkpoint_config.get("name_prefix", "ppo_simple_quadruped")),
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    model = PPO(
        policy="MlpPolicy",
        env=env,
        tensorboard_log=str(log_dir),
        seed=seed,
        device=config.get("device", "auto"),
        verbose=1,
        **ppo_config,
    )
    model.learn(total_timesteps=total_timesteps, callback=callback, progress_bar=False)
    model.save(str(final_model))
    env.close()

    print(f"Saved final model to {final_model}")


if __name__ == "__main__":
    main()
