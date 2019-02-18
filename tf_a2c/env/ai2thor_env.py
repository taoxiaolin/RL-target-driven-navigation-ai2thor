import ai2thor.controller
import numpy as np
import gym
import cv2
import h5py
import os
import sys
import random

from copy import deepcopy
from gym import error, spaces
from gym.utils import seeding

ALL_POSSIBLE_ACTIONS = [
    'MoveAhead',
    'MoveBack',
    'RotateRight',
    'RotateLeft',
    # 'Stop'   
]

class AI2ThorDumpEnv():
    """
    Wrapper base class
    """
    def __init__(self, scene, target, config, arguments=dict(), seed=None):
        """
        :param seed: (int)   Random seed
        :param config: (str)   Dictionary file storing cofigurations
        :param: scene: (list)  Scene to train on
        :param: objects: (list)  Target object to train on
        """
        
        self.config = config
        self.scene = scene
        self.target = target
        self.history_size = arguments.get('history_size')
        self.train_resnet = arguments.get('train_resnet')

        self.h5_file = h5py.File("{}.hdf5".format(os.path.join(config['dump_path'], self.scene)), 'r')

        all_visible_objects = set(",".join([o for o in list(self.h5_file['visible_objects']) if o != '']).split(','))
        
        assert self.target in all_visible_objects, "Target {} is unreachable in !".format(self.target, self.scene)

        self.states = self.h5_file['locations'][()]
        self.graph = self.h5_file['graph'][()]
        self.features = self.h5_file['resnet_features'][()]
        self.visible_objects = self.h5_file['visible_objects'][()]

        self.target_ids = [idx for idx in range(len(self.states)) if self.target in self.visible_objects[idx].split(",")]

        self.action_space = self.graph.shape[1]
        self.cv_action_onehot = np.identity(self.action_space)
        
        # Randomness settings
        self.np_random = None
        if seed:
            self.seed(seed)
        
        if self.train_resnet:
            self.observations = self.h5_file['observations'][()]
            self.resolution = self.observations[0].shape

            self.history_states = np.zeros((self.history_size, self.resolution[0], \
                                            self.resolution[1], self.resolution[2]))
        else:
            self.history_states = np.zeros((self.history_size, self.features.shape[1]))

    def step(self, action):
        '''
        0: move ahead
        1: move back
        2: rotate right
        3: rotate left
        4: look down
        5: look up
        '''

        if action >= self.action_space:
            raise error.InvalidAction('Action must be an integer between '
                                      '0 and {}!'.format(self.action_space - 1))
        k = self.current_state_id
        if self.graph[k][action] != -1:
            self.current_state_id = int(self.graph[k][action])
            if self.current_state_id in self.target_ids:
                self.terminal = True
                collided = False
            else:
                self.terminal = False
                collided = False
        else:
            self.terminal = False
            collided = True

        reward, done = self.transition_reward(collided)

        self.tiled_states()

        return self.history_states, reward, done

    def transition_reward(self, collided):
        reward = self.config['default_reward']
        done = 0
        if self.terminal:
            reward = self.config['success_reward']
            done = 1
        elif self.config['anti-collision'] and collided:
            reward = self.config['collide_reward']

        return reward, done

    def reset(self):
        # reset parameters
        self.current_state_id = random.randrange(self.states.shape[0])
        self.tiled_states()
        self.terminal = False

        return self.history_states, self.target

    def tiled_states(self):
        if self.train_resnet:
            o = self.observations[self.current_state_id]
            self.history_states = np.append(self.history_states[1:, :], np.expand_dims(o, 0), 0)
        else:
            f = self.features[self.current_state_id]
            self.history_states = np.append(self.history_states[1:, :], np.transpose(f, (1,0)), 0)

    def render(self, mode='human'):
        raise NotImplementedError

    def seed(self, seed=None):
        self.np_random, seed1 = seeding.np_random(seed)
        # Derive a random seed. This gets passed as a uint, but gets
        # checked as an int elsewhere, so we need to keep it below
        # 2**31.
        return seed1

if __name__ == '__main__':
    AI2ThorEnv()
