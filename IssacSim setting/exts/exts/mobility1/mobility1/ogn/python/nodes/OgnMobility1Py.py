import numpy as np
from omni.isaac.core.scenes import Scene
from omni.isaac.core.articulations import Articulation
import omni.isaac.core.utils.xforms as xforms_utils
import omni.isaac.core.utils.numpy as numpy_utils
from omni.isaac.core.utils.types import ArticulationActions
from omni.isaac.core.prims import XFormPrim
import time
from influxdb import InfluxDBClient
from datetime import datetime


class OgnMobility1PyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.initialized = None
        self.status = False
        self.prim_path = "/World/transporter_01"
        # self.lack_prim_path="/World/RackSmall_A1"
        self.IP_address = "192.168.0.104"
        self.client = InfluxDBClient(host=self.IP_address, port=8086, username="admin", password="12345", database="solutionist")

        self.transporter = Articulation(prim_path=self.prim_path)
        self.current_transporter_position = None
        self.current_transporter_orientation = None

        self.object=XFormPrim("/World/purpose_position2")
        self.position,_=self.object.get_world_pose()
        # print(f"position: {self.position}")
        self.target_transporter_position = self.position
        self.target_transporter_orientation = numpy_utils.euler_angles_to_quats(np.array([0.0,0.0,0.0]))
        self.state = "move_forward_y"    
        self.state_time=0   
        self.arrived = 0

    def initialize_scene(self):
        
        self.transporter.initialize()
        # self.lack.initialize()
        self.initialized = True
        self.transporter_position, self.transporter_orientation = self.transporter.get_world_pose()
        # print(self.transporter_position)
    def move_cw(self):
        while True:
            _, self.current_transporter_orientation = self.transporter.get_world_pose()
            current_angle = numpy_utils.quats_to_euler_angles(self.current_transporter_orientation)[2]
            target_angle = numpy_utils.quats_to_euler_angles(self.target_transporter_orientation)[2]
            
            angle_diff = target_angle - current_angle
            
            # 각도 차이가 임계값보다 큰 경우에만 회전
            if abs(angle_diff) > 0.03:
                velocity = np.array([5.0,-5.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                return control_actions
            else:
                # 목표 각도에 도달하면 정지
                velocity = np.array([0.0,0.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                self.state_time += 1
                if self.state_time >= 60:  # 60 프레임 = 약 1초
                    self.state = "move_forward_y"
                    self.state_time = 0
                return control_actions, 1

                break
    def move_ccw(self):
        while True:
            _, self.current_transporter_orientation = self.transporter.get_world_pose()
            current_angle = numpy_utils.quats_to_euler_angles(self.current_transporter_orientation)[2]
            target_angle = numpy_utils.quats_to_euler_angles(self.target_transporter_orientation)[2]
            # print(f"current_angle: {current_angle}")
            # print(f"target_angle: {target_angle}")
            
            angle_diff = target_angle - current_angle
            
            # 각도 차이가 임계값보다 큰 경우에만 회전
            if abs(angle_diff) > 0.07:
                velocity = np.array([-3.0,3.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                return control_actions
            else:
                # 목표 각도에 도달하면 정지
                velocity = np.array([0.0,0.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                # self.state = "move_forward_y"
                self.state_time += 1
                if self.state_time >= 60:  # 60 프레임 = 약 1초
                    self.state = "move_forward_x"
                    self.state_time = 0
                return control_actions
                break
    def move_forward(self,distance,axis):
        if axis == "x":
            i = 0
        elif axis == "y":
            i = 1
        while True:
            current_position, _ = self.transporter.get_world_pose()
            # print(f"current_position: {current_position[i]}")
            target_position = distance 
            # print(f"target_position: {target_position}")
            
            # 현재 위치와 목표 위치의 차이 계산
            position_diff = abs(current_position[i] - target_position)
            # print(position_diff)
            
            if position_diff > 0.1:
                # 목표지점까지 이동
                velocity = np.array([12.0,12.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                return control_actions
                # self.transporter._articulation_view.apply_action(control_actions)
            else:
                # 목표 위치에 도달하면 완전히 정지
                velocity = np.array([0.0,0.0,0,0,0,0,0])
                control_actions = ArticulationActions(joint_velocities=velocity)
                if axis == "y":
                    self.state = "move_ccw"
                elif axis == "x":
                    # self.state = "stop"
                    self.arrived =1
                return control_actions
            
                break
    def stop(self):
        velocity = np.array([0.0,0.0,0,0,0,0,0])
        control_actions = ArticulationActions(joint_velocities=velocity)
        return control_actions


class OgnMobility1Py:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnMobility1PyInternalState()

    @staticmethod
    def compute(db) -> bool:
        """Compute the output based on inputs and internal state"""
        state = db.internal_state

    @staticmethod
    def compute(db) -> bool:
        
        try:
            state = db.internal_state
            if not state.initialized:
                state.initialize_scene()
            if not hasattr(state, 'input_state') or db.inputs.inputAttribute1 == 1:
                state.input_state = db.inputs.inputAttribute1
            if state.input_state == 1:
                if state.state == "move_forward_y":
                    control_actions = state.move_forward(state.target_transporter_position[1],"y")
                    state.transporter._articulation_view.apply_action(control_actions)
                elif state.state == "move_ccw":
                    control_actions = state.move_ccw()
                    state.transporter._articulation_view.apply_action(control_actions)
                elif state.state == "move_forward_x":
                    control_actions = state.move_forward(state.target_transporter_position[0],"x")
                    state.transporter._articulation_view.apply_action(control_actions)
            db.outputs.outputAttribute1 = state.arrived
                # elif state.state == "stop":
                #     control_actions = state.stop()
                    # state.transporter._articulation_view.apply_action(control_actions)
            

            
            # Write to InfluxDB
            # state.client.write_points([data_point])

            
            # Set output attribute
            
        except Exception as e:
            db.log_error(f"Computation error: {str(e)}")
            return False
        return True
