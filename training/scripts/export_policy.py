"""Export the deterministic PPO actor to ONNX and verify ONNXRuntime parity."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
import torch
import yaml
from stable_baselines3 import PPO

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sim.envs import SimpleQuadrupedEnv


class DeterministicActor(torch.nn.Module):
    """Minimal actor-only wrapper around an SB3 ActorCriticPolicy."""

    def __init__(self, model: PPO) -> None:
        super().__init__()
        self.features_extractor = model.policy.features_extractor
        self.policy_net = model.policy.mlp_extractor.policy_net
        self.action_net = model.policy.action_net

    def forward(self, observation: torch.Tensor) -> torch.Tensor:
        features = self.features_extractor(observation)
        latent_pi = self.policy_net(features)
        return torch.clamp(self.action_net(latent_pi), -1.0, 1.0)


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
        default=Path("models/onnx/simple_quadruped_actor.onnx"),
        help="Output ONNX path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("models/reports/simple_quadruped_actor_onnx.json"),
        help="Output JSON verification report.",
    )
    parser.add_argument("--samples", type=int, default=32, help="Number of observations used for parity checks.")
    parser.add_argument("--seed", type=int, default=None, help="Verification seed. Defaults to config seed.")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version.")
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
    )


def collect_observations(env: SimpleQuadrupedEnv, count: int, seed: int) -> np.ndarray:
    observations: list[np.ndarray] = []
    obs, _ = env.reset(seed=seed)
    observations.append(obs)
    while len(observations) < count:
        action = env.action_space.sample()
        obs, _, terminated, truncated, _ = env.step(action)
        observations.append(obs)
        if terminated or truncated:
            obs, _ = env.reset(seed=seed + len(observations))
            observations.append(obs)
    return np.asarray(observations[:count], dtype=np.float32)


def sb3_predict_batch(model: PPO, observations: np.ndarray) -> np.ndarray:
    actions = []
    for obs in observations:
        action, _ = model.predict(obs, deterministic=True)
        actions.append(action)
    return np.asarray(actions, dtype=np.float32)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    seed = args.seed if args.seed is not None else int(config.get("seed", 0))
    env_config = config.get("env", {})
    paths_config = config.get("paths", {})

    model_path = args.model or Path(paths_config.get("final_model", "training/checkpoints/ppo_simple_quadruped/final_model.zip"))
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = PPO.load(str(model_path), env=None, device="cpu")
    actor = DeterministicActor(model).eval()

    obs_dim = int(model.observation_space.shape[0])
    action_dim = int(model.action_space.shape[0])
    dummy_obs = torch.zeros((1, obs_dim), dtype=torch.float32)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        actor,
        dummy_obs,
        str(args.output),
        export_params=True,
        opset_version=args.opset,
        do_constant_folding=True,
        input_names=["observation"],
        output_names=["action"],
        dynamic_axes={"observation": {0: "batch"}, "action": {0: "batch"}},
    )

    onnx_model = onnx.load(str(args.output))
    onnx.checker.check_model(onnx_model)

    env = make_env(env_config)
    observations = collect_observations(env=env, count=args.samples, seed=seed)
    env.close()

    with torch.no_grad():
        torch_actions = actor(torch.as_tensor(observations, dtype=torch.float32)).numpy()
    sb3_actions = sb3_predict_batch(model=model, observations=observations)

    session = ort.InferenceSession(str(args.output), providers=["CPUExecutionProvider"])
    onnx_actions = session.run(["action"], {"observation": observations})[0]

    torch_onnx_abs_diff = np.abs(torch_actions - onnx_actions)
    sb3_onnx_abs_diff = np.abs(sb3_actions - onnx_actions)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "source_model": str(model_path),
        "onnx_model": str(args.output),
        "opset": args.opset,
        "samples": int(args.samples),
        "observation_dim": obs_dim,
        "action_dim": action_dim,
        "torch_vs_onnx_max_abs_diff": float(torch_onnx_abs_diff.max()),
        "torch_vs_onnx_mean_abs_diff": float(torch_onnx_abs_diff.mean()),
        "sb3_vs_onnx_max_abs_diff": float(sb3_onnx_abs_diff.max()),
        "sb3_vs_onnx_mean_abs_diff": float(sb3_onnx_abs_diff.mean()),
        "action_min": float(onnx_actions.min()),
        "action_max": float(onnx_actions.max()),
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(json.dumps(report, indent=2))
    print(f"Saved ONNX model to {args.output}")
    print(f"Saved verification report to {args.report}")


if __name__ == "__main__":
    main()
