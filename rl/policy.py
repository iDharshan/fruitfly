"""
Neural Network Policy and Custom Feature Extractor for Fruitfly V2.
Extracts biological and task features using compact specialized sub-networks.
"""

from typing import Dict, Tuple, Optional
import numpy as np

try:
    import torch
    import torch.nn as nn
    from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
except ImportError:
    # Graceful fallback before torch installation completes
    torch = None
    nn = None
    BaseFeaturesExtractor = object


if torch is not None and nn is not None:
    class FruitFlyFeaturesExtractor(BaseFeaturesExtractor):
        """
        Specialized Dict feature extractor for Fruitfly V2.
        Processes each semantic sub-observation through a dedicated projection layer:
          - compass (5) -> 32
          - sensory (8) -> 32
          - odor (4) -> 16
          - pigment (5) -> 16
          - kinematics (4) -> 16
          - task (16, 16, 3) -> 64
        Total concatenated feature representation: 176 dimensions.
        """

        def __init__(self, observation_space, features_dim: int = 176):
            super().__init__(observation_space, features_dim=features_dim)

            self.compass_net = nn.Sequential(
                nn.Linear(5, 32),
                nn.ReLU(),
            )
            self.sensory_net = nn.Sequential(
                nn.Linear(8, 32),
                nn.ReLU(),
            )
            self.odor_net = nn.Sequential(
                nn.Linear(4, 16),
                nn.ReLU(),
            )
            self.pigment_net = nn.Sequential(
                nn.Linear(5, 16),
                nn.ReLU(),
            )
            self.kinematics_net = nn.Sequential(
                nn.Linear(4, 16),
                nn.ReLU(),
            )
            # Task disparity (16, 16, 3) = 768 elements
            self.task_net = nn.Sequential(
                nn.Flatten(),
                nn.Linear(16 * 16 * 3, 64),
                nn.ReLU(),
            )

        def forward(self, observations: Dict[str, torch.Tensor]) -> torch.Tensor:
            c = self.compass_net(observations["compass"])
            s = self.sensory_net(observations["sensory"])
            o = self.odor_net(observations["odor"])
            p = self.pigment_net(observations["pigment"])
            k = self.kinematics_net(observations["kinematics"])
            t = self.task_net(observations["task"])
            return torch.cat([c, s, o, p, k, t], dim=1)
else:
    class FruitFlyFeaturesExtractor:
        pass
