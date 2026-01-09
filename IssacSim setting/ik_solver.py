from omni.isaac.motion_generation import ArticulationKinematicsSolver, LulaKinematicsSolver
from omni.isaac.core.articulations import Articulation
from typing import Optional
import numpy as np

import sys
# sys.path.append(r"C:\isaacsim\kit\python\Lib")


class KinematicsSolver(ArticulationKinematicsSolver):
    def __init__(self, robot_articulation: Articulation, end_effector_frame_name: Optional[str] = None) -> None:
        self._kinematics = LulaKinematicsSolver(
            robot_description_path=r"C:/isaacsim_4.2.0/intelligence/robot_descriptor.yaml",
            urdf_path=r"C:/isaacsim_4.2.0/intelligence/ujin_isaacsim/urdf/indy7.urdf"
        )
        if end_effector_frame_name is None:
            end_effector_frame_name = "tcp"
        ArticulationKinematicsSolver.__init__(self, robot_articulation, self._kinematics, end_effector_frame_name)
    def set_robot_base_pose(self, robot_positions: np.ndarray, robot_orientation: np.ndarray):
        self._kinematics.set_robot_base_pose(robot_positions, robot_orientation)
