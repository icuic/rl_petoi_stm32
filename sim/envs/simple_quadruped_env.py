"""Minimal MuJoCo quadruped environment for interface bring-up."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from sim.envs.simple_quadruped_interface import (
    ACTION_DIM,
    ACTION_SCALE_RAD,
    NEUTRAL_POSE_RAD,
    OBSERVATION_DIM,
    normalized_action_to_joint_targets,
)


class SimpleQuadrupedEnv(gym.Env):
    """A small 8-DoF quadruped controlled by normalized joint targets."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 50}

    def __init__(
        self,
        model_path: str | Path | None = None,
        frame_skip: int = 10,
        episode_steps: int = 1000,
        reward_config: dict[str, float] | None = None,
        reset_config: dict[str, float] | None = None,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        if render_mode not in (None, "rgb_array"):
            raise ValueError(f"Unsupported render_mode: {render_mode}")

        root_dir = Path(__file__).resolve().parents[2]
        self.model_path = Path(model_path) if model_path else root_dir / "sim" / "robots" / "simple_quadruped.xml"
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)

        self.frame_skip = frame_skip
        self.episode_steps = episode_steps
        self.render_mode = render_mode
        self.step_count = 0
        self.phase = 0.0
        self._renderer: mujoco.Renderer | None = None
        self.previous_action = np.zeros(8, dtype=np.float32)
        self.reset_config = {
            "torso_height": 0.22,
            "joint_noise": 0.02,
            "velocity_noise": 0.01,
        }
        if reset_config:
            self.reset_config.update({key: float(value) for key, value in reset_config.items()})
        self.reward_config = {
            "survival": 0.1,
            "forward": 1.0,
            "upright": 0.2,
            "target_height": 0.22,
            "height": 0.5,
            "roll": 0.15,
            "pitch": 0.05,
            "xy_velocity": 0.0,
            "vertical_velocity": 0.0,
            "angular_velocity": 0.005,
            "joint_velocity": 0.0005,
            "joint_position": 0.0,
            "action": 0.002,
            "action_delta": 0.001,
            "drift": 0.0,
            "fall": 0.2,
        }
        if reward_config:
            self.reward_config.update({key: float(value) for key, value in reward_config.items()})

        self.joint_qpos_addr = np.arange(7, 15)
        self.joint_qvel_addr = np.arange(6, 14)
        self.neutral_pose = NEUTRAL_POSE_RAD.copy()
        self.action_scale = ACTION_SCALE_RAD.copy()

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(OBSERVATION_DIM,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.step_count = 0
        self.phase = 0.0
        self.previous_action = np.zeros(8, dtype=np.float32)

        joint_noise = float(self.reset_config["joint_noise"])
        velocity_noise = float(self.reset_config["velocity_noise"])

        self.data.qpos[:7] = np.array([0.0, 0.0, self.reset_config["torso_height"], 1.0, 0.0, 0.0, 0.0])
        self.data.qpos[self.joint_qpos_addr] = self.neutral_pose
        self.data.qpos[self.joint_qpos_addr] += self.np_random.uniform(-joint_noise, joint_noise, size=8)
        self.data.qvel[:] = self.np_random.uniform(-velocity_noise, velocity_noise, size=self.model.nv)
        self.data.ctrl[:] = self.neutral_pose
        mujoco.mj_forward(self.model, self.data)

        return self._get_obs(), {"phase": self.phase}

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, self.action_space.low, self.action_space.high)

        target = normalized_action_to_joint_targets(action)
        self.data.ctrl[:] = target
        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)

        self.step_count += 1
        self.phase = (self.phase + 0.02) % 1.0

        health = self._get_health()
        termination_reason = health["termination_reason"]
        terminated = termination_reason != "healthy"
        truncated = self.step_count >= self.episode_steps
        if truncated and not terminated:
            termination_reason = "timeout"
        obs = self._get_obs()
        reward, reward_terms = self._get_reward(action=action, health=health, terminated=terminated)
        info = {
            "x_position": float(self.data.qpos[0]),
            "x_velocity": float(self.data.qvel[0]),
            "phase": self.phase,
            "torso_height": health["height"],
            "roll": health["roll"],
            "pitch": health["pitch"],
            "termination_reason": termination_reason,
            "reward_terms": reward_terms,
        }
        self.previous_action = action.copy()
        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode != "rgb_array":
            return None
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, width=640, height=480)
        self._renderer.update_scene(self.data)
        return self._renderer.render()

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    def _get_obs(self) -> np.ndarray:
        phase_angle = 2.0 * np.pi * self.phase
        obs = np.concatenate(
            [
                self.data.qpos[2:3],
                self.data.qpos[3:7],
                self.data.qvel[0:6],
                self.data.qpos[self.joint_qpos_addr],
                self.data.qvel[self.joint_qvel_addr],
                np.array([np.sin(phase_angle), np.cos(phase_angle)]),
            ]
        )
        return obs.astype(np.float32)

    def _get_reward(self, action: np.ndarray, health: dict[str, float | str], terminated: bool) -> tuple[float, dict[str, float]]:
        weights = self.reward_config
        roll = float(health["roll"])
        pitch = float(health["pitch"])
        action_delta = action - self.previous_action

        terms = {
            "survival": weights["survival"],
            "forward": weights["forward"] * float(self.data.qvel[0]),
            "upright": weights["upright"] * float(self.data.qpos[3]),
            "height_penalty": weights["height"] * abs(float(health["height"]) - weights["target_height"]),
            "roll_penalty": weights["roll"] * roll * roll,
            "pitch_penalty": weights["pitch"] * pitch * pitch,
            "xy_velocity_penalty": weights["xy_velocity"] * float(np.square(self.data.qvel[0:2]).sum()),
            "vertical_velocity_penalty": weights["vertical_velocity"] * float(self.data.qvel[2] * self.data.qvel[2]),
            "angular_velocity_penalty": weights["angular_velocity"] * float(np.square(self.data.qvel[3:6]).sum()),
            "joint_velocity_penalty": weights["joint_velocity"] * float(np.square(self.data.qvel[self.joint_qvel_addr]).sum()),
            "joint_position_penalty": weights["joint_position"] * float(np.square(self.data.qpos[self.joint_qpos_addr] - self.neutral_pose).sum()),
            "action_penalty": weights["action"] * float(np.square(action).sum()),
            "action_delta_penalty": weights["action_delta"] * float(np.square(action_delta).sum()),
            "drift_penalty": weights["drift"] * float(np.square(self.data.qpos[0:2]).sum()),
            "fall_penalty": weights["fall"] if terminated else 0.0,
        }
        reward = (
            terms["survival"]
            + terms["forward"]
            + terms["upright"]
            - terms["height_penalty"]
            - terms["roll_penalty"]
            - terms["pitch_penalty"]
            - terms["xy_velocity_penalty"]
            - terms["vertical_velocity_penalty"]
            - terms["angular_velocity_penalty"]
            - terms["joint_velocity_penalty"]
            - terms["joint_position_penalty"]
            - terms["action_penalty"]
            - terms["action_delta_penalty"]
            - terms["drift_penalty"]
            - terms["fall_penalty"]
        )
        return float(reward), terms

    def _get_health(self) -> dict[str, float | str]:
        height = float(self.data.qpos[2])
        quat = self.data.qpos[3:7]
        roll, pitch = _quat_to_roll_pitch(quat)

        if height < 0.08:
            termination_reason = "torso_too_low"
        elif height > 0.45:
            termination_reason = "torso_too_high"
        elif abs(roll) > 1.2:
            termination_reason = "roll_too_large"
        elif abs(pitch) > 1.2:
            termination_reason = "pitch_too_large"
        else:
            termination_reason = "healthy"

        return {
            "height": height,
            "roll": roll,
            "pitch": pitch,
            "termination_reason": termination_reason,
        }


def _quat_to_roll_pitch(quat: np.ndarray) -> tuple[float, float]:
    w, x, y, z = quat
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))
    return float(roll), float(pitch)
