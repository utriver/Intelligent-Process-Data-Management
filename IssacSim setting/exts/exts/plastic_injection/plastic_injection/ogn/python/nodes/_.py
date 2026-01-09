import numpy as np
import carb
from omni.isaac.core_nodes import BaseResetNode
from omni.isaac.core.articulations import Articulation
from omni.isaac.manipulators import SingleManipulator
# from omni.isaac.motion_generation import ArticulationMotionKinematicsSolver
# 역기구학 모듈
from ik_solver import KinematicsSolver
from typing import Optional
from omni.isaac.core.scenes import Scene
from omni.graph.core import Database
import omni.isaac.core.utils.xforms as xforms_utils
from isaacsim.sensors.physx import _range_sensor
from omni.isaac.core.utils.rotations import quat_to_euler_angles
import isaacsim.core.utils.prims as prims_utils
from isaacsim.core.api.objects import VisualCuboid
from omni.isaac.core.utils.types import ArticulationAction
import time

class OgnCustomConveyorNodePyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.status = False
        self.initialized = False
        self.lidar_sensor_interface = None
        self.robot_prim_path = "/World/indy7_01"          # 로봇 경로
        self.tcp_prim_path = "/World/indy7_01/link6"        # TCP 경로
        self.robot_name = "indy7_01"                      # 로봇 이름
        self.tcp_name = "tcp"                                   # TCP 이름
        self.scene = None
        self.manipulator = None
        self.my_robot = None
        self.my_controller = None
        self.articulation_controller = None
        self.cube_initial_position = None
        self.cube_initial_rotation = None
        self.current_state = "idle"
        self.target_reached = False
        self.move_started = False
        self.last_action_time = 0
    
    def initialize_scene(self):
        """Initialize the scene"""
        self.lidar_sensor_interface = _range_sensor.acquire_lidar_sensor_interface()
        
        # Scene 객체 생성 - 시뮬레이션 환경을 관리
        self.scene = Scene()
        # 로봇 매니퓰레이터 객체 초기화
        self.manipulator = SingleManipulator(
            prim_path=self.robot_prim_path,
            name=self.robot_name,
            end_effector_prim_path=self.tcp_prim_path,
        )
        # 생성된 매니퓰레이터를 씬에 추가
        self.scene.add(self.manipulator)


        # 매니퓰레이터 초기화
        self.manipulator.initialize()
        
        ####### 로봇 객체와 제어기 설정 #######
        # 씬에서 로봇 객체 참조
        self.my_robot = self.scene.get_object(self.robot_name)   
        
        # 역기구학 제어기에 로봇 객체 전달                   
        self.my_controller = KinematicsSolver(self.my_robot)       
        
        # 로봇 객체의 관절 제어기 획득                 
        self.articulation_controller = self.my_robot.get_articulation_controller()
        
        self.initialized = True
        cube_path = "/World/Cube"
        self.cube_initial_position = xforms_utils.get_world_pose(cube_path)[0]
        self.cube_initial_rotation = xforms_utils.get_world_pose(cube_path)[1]
         
    def reset(self):
        """Reset the state"""
        self.initialized = False
        self.scene = None
        self.manipulator = None
        self.my_robot = None
        self.my_controller = None
        self.articulation_controller = None
        self.target_reached = False
        self.move_started = False
        self.current_state = "idle"
        try:
            cube_path = "/World/Cube"
            tcp_path = "/World/indy7_01/link6/tcp"
            
            if prims_utils.is_prim_path_valid(tcp_path):
                prims_utils.reset_xform_stack(tcp_path)
                prims_utils.move_prim(tcp_path, "/World/Cube")
            if self.cube_initial_position is not None and self.cube_initial_rotation is not None:
                xforms_utils.set_world_pose(cube_path, self.cube_initial_position, self.cube_initial_rotation)
        except Exception as e:
            carb.log_warn(f"Failed to reset cube position:{e} ")

class OgnCustomConveyorNodePy:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnCustomConveyorNodePyInternalState()

    @staticmethod
    def compute(db) -> bool:
        """Compute the output based on inputs and internal state"""
        state = db.internal_state
        db.outputs.outputAttribute1 = True
        
        # Initialize constants
        go = 1.0
        stop = 0.0
        
        # Default output is go - 컨베이어 계속 작동
        db.outputs.outputAttribute2 = go
        
        try:
            if not state.initialized:
                state.initialize_scene()
                
            # 그 다음 라이다 센서 데이터 확인
            sensor_path = "/World/Lidar"   
            
            if state.lidar_sensor_interface:
                intensity_data = state.lidar_sensor_interface.get_linear_depth_data(sensor_path)
                
                print(f"intensity_data: {intensity_data}")
                print(f"current_state: {state.current_state}")
                # 물체가 감지되면(depth < 0.5) 로봇 동작 시작 (컨베이어는 계속 작동)
                if state.current_state == "idle":
                    # 조인트 각도를 모두 0으로 초기화
                

                        
                    # 6개 조인트 모두 0으로 설정
                    zero_joint_positions = ArticulationAction(np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
                    
                    # 관절 위치 적용
                    state.articulation_controller.apply_action(zero_joint_positions)
                    print("All joint angles set to zero")
                if intensity_data is not None and intensity_data < 0.3 and state.current_state == "idle":
                    # 컨베이어 계속 작동 (stop 명령 제거)
                    db.outputs.outputAttribute2 = stop
                    state.current_state = "detected"
                    state.move_started = True
                    state.last_action_time = time.time()
                    print("Object detected, robot starting operation")
                
                # 물체 감지 후 로봇 동작 시작
                if state.current_state == "detected" and state.move_started:
                    # 큐브의 위치와 방향 가져오기
                    db.outputs.outputAttribute2 = stop
                    cube_path = "/World/Cube"
                    if prims_utils.is_prim_path_valid(cube_path):
                        position, quaternion = xforms_utils.get_world_pose(cube_path)
                        position[2] += 0.07  # 약간 위로 들어올리기
                        print(f"position: {position}")
                        print(f"quaternion: {quaternion}")
                        # 역기구학 계산 수행
                        actions, succ = state.my_controller.compute_inverse_kinematics(
                            target_position=np.array(position),
                            target_orientation=np.array(quaternion)
                        )
                        # print(f"actions: {actions}")
                        # print(f"succ: {succ}")
                         
                        if succ:
                            # 역기구학 계산이 성공했으면 관절 동작 적용
                            state.articulation_controller.apply_action(actions)
                            
                            # 로봇이 목표 위치에 도달했는지 확인 (시간 기반)
                            current_time = time.time()
                            if current_time - state.last_action_time > 1.5:  # 2초 후에 도달했다고 가정
                                state.target_reached = True
                                state.current_state = "reached"
                                print("Robot reached target position")
                                print(f"current_state: {state.target_reached}")
                        else:
                            # 해를 찾지 못했을 경우 경고 메시지 출력
                            carb.log_warn(f"IK did not converge to a solution for target {position}. No action is being taken.")
                
                # 로봇이 목표 위치에 도달했으면 큐브를 TCP에 부착
                if state.current_state == "reached" :
                    
                    db.outputs.outputAttribute2 = stop
                    cube_path = "/World/Cube"
                    tcp_path = "/World/indy7_01/link6/tcp"
                    
                    if prims_utils.is_prim_path_valid(cube_path) and prims_utils.is_prim_path_valid(tcp_path):
                        # 큐브를 TCP에 이동
                        prims_utils.move_prim(cube_path, f"{tcp_path}/Cube")
                        state.current_state = "moving"
                        print("Cube attached to TCP")
                    
                    
                if state.current_state == "moving":
                    # 로봇이 moving 상태일 때 1번 조인트를 180도 반시계 방향으로 회전
                    db.outputs.outputAttribute2 = stop
                    
                    # 현재 시간 확인
                    current_time = time.time()
                    
                    # 목표 관절 위치 설정 - 로봇을 원래 위치로 되돌리기 위한 관절 각도
                    target_joint_positions = ArticulationAction(np.array([95.7*np.pi/180, 0.0, -60.4*np.pi/180, -3.2*np.pi/180, -82.6*np.pi/180, 0.0*np.pi/180]))  # 예시 관절 각도
                    
                    # 관절 위치 적용
                    state.articulation_controller.apply_action(target_joint_positions)
                    
                    # 동작 완료 후 상태 변경 (일정 시간 후)
                    if current_time - state.last_action_time > 5.0:  # 3초 후에 동작 완료로 간주
                        state.current_state = "completed"
                        print("Robot moved to target position")
                        
                        # 디버깅을 위한 출력 
                        print(f"Robot object type: {type(state.my_robot)}")
                        print(f"Robot object: {state.my_robot}")

                # 관절 위치 확인은 completed 상태에서 수행 
                if state.current_state == "completed":
                    try:
                        # 목표 위치 설정 (0.2, 0.6, 0.5)
                        cube_path = "/World/Cube"
                        tcp_path = "/World/indy7_01/link6/tcp"
                        target_position = np.array([0.071, 0.6, 0.5])
                        
                        target_orientation = np.array([0.0,-1.0,0.0,0.0])  # 기본 쿼터니언 (w, x, y, z)
                        
                        # 역기구학 계산
                        actions, succ = state.my_controller.compute_inverse_kinematics(
                            target_position=target_position,
                            target_orientation=target_orientation
                        )
                        
                        print(f"actions: {actions}")
                        state.articulation_controller.apply_action(actions)
                        # 관절 위치 적용 후 상태를 place로 변경
                        state.current_state = "place"
                        
                        # else:
                        #     print(f"Failed to find IK solution for position {target_position}")
                    except Exception as e:
                        print(f"Error in completed state: {e}")
                if state.current_state == "place":
            # 로봇이 목표 위치에 도달했는지 확인 (시간 기반)
                    try:
                        current_time = time.time()
                        if current_time - state.last_action_time > 1.0:  # 2초 후에 도달했다고 가정
                        # 목표 위치에 도달한 후에 큐브를 원래 위치로 이동
                            prims_utils.move_prim(f"{tcp_path}/Cube", cube_path)
                            print("Cube detached from TCP and moved back to original position")
                            state.current_state = "idle"  # 작업 완료 후 idle 상태로 변경
                            state.target_reached = False
                            state.last_action_time = time.time()  # 타이머 재설정
                    except Exception as e:
                        print(f"Error in completed state: {e}")
                # 모든 동작이 완료된 상태
                if state.current_state == "completed":
                    # 컨베이어 다시 작동
                    db.outputs.outputAttribute2 = go
                    state.current_state = "idle"
                    state.target_reached = False
                    state.last_action_time = time.time()  # 타이머 재설정
                    # 필요한 경우 여기에 추가 작업 구현
                    
        except Exception as e:
            db.log_error(f"Computation error: {e}")
            return False
            
        return True

    @staticmethod
    def release_instance(node, graph_instance_id):
        try:
            print('release_instance')
            
            # 현재 노드의 내부 상태를 Database에서 가져옴
            # per_instance_internal_state는 각 노드 인스턴스별로 고유한 상태를 관리
            state = Database.per_instance_internal_state(node)
        except Exception:
            state = None
            pass
        
        if state is not None:
            print('state is not None reset')
            # 노드의 상태가 존재하면 reset() 메서드를 호출하여 초기화
            # 시뮬레이션 정지나 재시작 시 리소스를 정리하고 초기 상태로 복원
            state.reset()
