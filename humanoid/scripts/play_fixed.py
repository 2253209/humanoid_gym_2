'''
    将机器人吊起来测试模型。
    需要指定一个转换成CPU的模型路径（）
    需要指定--task=zq12

    1.obs 中的 omega，euler，pos，vel已经设置为0
    2.cmd 都为0
    3.有值的只有cos[2]和action[12]
'''
import time

from humanoid import LEGGED_GYM_ROOT_DIR
import os

import isaacgym
from humanoid.envs import *
from humanoid.utils import  get_args, export_policy_as_jit, task_registry

import numpy as np
import torch
from deploy.utils.logger import SimpleLogger, get_title_short

def play(args):
    args.task = 'zq'
    env_cfg, train_cfg = task_registry.get_cfgs(name=args.task)
    # override some parameters for testing
    env_cfg, train_cfg = task_registry.get_cfgs(name=args.task)
    # override some parameters for testing
    env_cfg.env.num_envs = min(env_cfg.env.num_envs, 1)
    env_cfg.sim.max_gpu_contact_pairs = 2**10
    # env_cfg.terrain.mesh_type = 'trimesh'
    env_cfg.terrain.mesh_type = 'plane'
    env_cfg.terrain.num_rows = 5
    env_cfg.terrain.num_cols = 5
    env_cfg.terrain.curriculum = False
    env_cfg.terrain.max_init_terrain_level = 5
    env_cfg.noise.add_noise = False
    env_cfg.domain_rand.push_robots = False
    env_cfg.domain_rand.joint_angle_noise = 0.
    env_cfg.noise.curriculum = False
    env_cfg.noise.noise_level = 0.5
    env_cfg.domain_rand.randomize_init_state = False
    env_cfg.asset.fix_base_link = False

    # prepare environment
    env, _ = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    obs = env.get_observations().to('cpu')
    # load policy
    train_cfg.runner.resume = True
    ppo_runner, train_cfg = task_registry.make_alg_runner(env=env, name=args.task, args=args, train_cfg=train_cfg)

    load_model = f'{LEGGED_GYM_ROOT_DIR}/logs/zq/exported/policies/policy_1.pt'
    policy = torch.jit.load(load_model)
    
    robot_index = 0 # which robot is used for logging
    joint_index = 1 # which joint is used for logging
    stop_state_log = 100 # number of steps before plotting states
    stop_rew_log = env.max_episode_length + 1 # number of steps before print average episode rewards
    camera_position = np.array(env_cfg.viewer.pos, dtype=np.float64)
    camera_vel = np.array([1., 1., 0.])
    camera_direction = np.array(env_cfg.viewer.lookat) - np.array(env_cfg.viewer.pos)
    img_idx = 0
    sloger = SimpleLogger(f'{LEGGED_GYM_ROOT_DIR}/logs/play_log', get_title_short())
    t1 = time.time()
    t0 = 0
    _first = True

    for i in range(10*int(env.max_episode_length)):
        # actions = policy(obs.detach())
        if i < 100:
            actions = torch.zeros((env.num_envs, env.num_actions))
            actions[:, :] = env.default_dof_pos[:]
        else:
            if _first:
                env.ref_count[:] = 0.
                _first = False
            actions = policy(obs.detach())  # * 0.
        # obs[:, -12:] = 0.
        # print('obs_action:', obs[0, -12:])
        # actions = policy(obs.detach())
        # print('action:', actions[0])
        # actions[:, :] = env.default_dof_pos[0, :]

        # 保存play save
        # obs[:, 2:35] = 0.
        sloger.save(torch.cat([obs, actions * env_cfg.control.action_scale], dim=1), i, t1 - t0)
        t0 = t1
        t1 = time.time()

        # 统一设置指令
        env.commands[:, 0] = 0.0
        env.commands[:, 1] = 0.0
        env.commands[:, 2] = 0.0
        env.commands[:, 3] = 0.0

        obs, _, rews, dones, infos = env.step(actions.detach())
        obs = obs.to('cpu')
        # obs[:, 5:35] = 0.
        if RECORD_FRAMES:
            if i % 2:
                filename = os.path.join(LEGGED_GYM_ROOT_DIR, 'logs', train_cfg.runner.experiment_name, 'exported', 'frames', f"{img_idx}.png")
                env.gym.write_viewer_image_to_file(env.viewer, filename)
                img_idx += 1 
        if MOVE_CAMERA:
            camera_position += camera_vel * env.dt
            env.set_camera(camera_position, camera_position + camera_direction)


if __name__ == '__main__':
    EXPORT_POLICY = True
    RECORD_FRAMES = False
    MOVE_CAMERA = False
    args = get_args()
    play(args)
