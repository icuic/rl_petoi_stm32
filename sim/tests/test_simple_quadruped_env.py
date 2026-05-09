import numpy as np

from sim.envs import SimpleQuadrupedEnv


def test_random_actions_run_without_nan():
    env = SimpleQuadrupedEnv()
    obs, info = env.reset(seed=7)

    assert obs.shape == env.observation_space.shape
    assert np.isfinite(obs).all()
    assert 0.0 <= info["phase"] < 1.0

    for _ in range(300):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == env.observation_space.shape
        assert np.isfinite(obs).all()
        assert np.isfinite(reward)
        assert 0.0 <= info["phase"] < 1.0
        assert info["termination_reason"] in {
            "healthy",
            "torso_too_low",
            "torso_too_high",
            "roll_too_large",
            "pitch_too_large",
            "timeout",
        }
        assert np.isfinite(info["torso_height"])
        assert np.isfinite(info["roll"])
        assert np.isfinite(info["pitch"])
        if terminated or truncated:
            obs, info = env.reset()

    env.close()
