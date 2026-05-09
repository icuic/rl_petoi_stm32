"""Minimal MuJoCo quadruped environment for interface bring-up."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces


class SimpleQuadrupedEnv(gym.Env):
    """A small 8-DoF quadruped controlled by normalized joint targets."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 50}

    def __init__(
        self,
        model_path: str | Path | None = None,
        frame_skip: int = 10,
        episode_steps: int = 1000,
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

        self.joint_qpos_addr = np.arange(7, 15)
        self.joint_qvel_addr = np.arange(6, 14)
        self.neutral_pose = np.array(
            [0.15, -0.75, 0.15, -0.75, -0.15, -0.75, -0.15, -0.75],
            dtype=np.float32,
        )
        self.action_scale = np.array([0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55], dtype=np.float32)

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(8,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(29,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.step_count = 0
        self.phase = 0.0

        self.data.qpos[:7] = np.array([0.0, 0.0, 0.22, 1.0, 0.0, 0.0, 0.0])
        self.data.qpos[self.joint_qpos_addr] = self.neutral_pose
        self.data.qpos[self.joint_qpos_addr] += self.np_random.uniform(-0.02, 0.02, size=8)
        self.data.qvel[:] = self.np_random.uniform(-0.01, 0.01, size=self.model.nv)
        self.data.ctrl[:] = self.neutral_pose
        mujoco.mj_forward(self.model, self.data)

        return self._get_obs(), {"phase": self.phase}

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, self.action_space.low, self.action_space.high)

        target = self.neutral_pose + action * self.action_scale
        self.data.ctrl[:] = target
        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)

        self.step_count += 1
        self.phase = (self.phase + 0.02) % 1.0

        obs = self._get_obs()
        reward = self._get_reward(action)
        terminated = self._is_unhealthy()
        truncated = self.step_count >= self.episode_steps
        info = {
            "x_position": float(self.data.qpos[0]),
            "x_velocity": float(self.data.qvel[0]),
            "phase": self.phase,
        }
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

    def _get_reward(self, action: np.ndarray) -> float:
        forward_reward = self.data.qvel[0]
        upright_reward = 0.2 * self.data.qpos[3]
        action_penalty = 0.002 * float(np.square(action).sum())
        height_penalty = 0.5 * abs(float(self.data.qpos[2]) - 0.22)
        return float(0.1 + forward_reward + upright_reward - action_penalty - height_penalty)

    def _is_unhealthy(self) -> bool:
        height = float(self.data.qpos[2])
        quat = self.data.qpos[3:7]
        roll, pitch = _quat_to_roll_pitch(quat)
        return height < 0.08 or height > 0.45 or abs(roll) > 1.2 or abs(pitch) > 1.2


def _quat_to_roll_pitch(quat: np.ndarray) -> tuple[float, float]:
    w, x, y, z = quat
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))
    return float(roll), float(pitch)
