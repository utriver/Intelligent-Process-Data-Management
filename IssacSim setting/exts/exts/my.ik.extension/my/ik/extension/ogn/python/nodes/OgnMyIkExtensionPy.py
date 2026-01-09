################## Follow Target 예제에 필요한 라이브러리 ##################
import numpy as np
import carb
import time
import csv
# 시뮬레이션 초기화 설정
from omni.isaac.core_nodes import BaseResetNode
from omni.isaac.core.scenes import Scene
from omni.graph.core import Database
from omni.isaac.core.utils.types import ArticulationAction
import omni.isaac.core.utils.prims as prims_utils
from omni.isaac.core.robots import Robot
from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport
import omni.kit.viewport.utility as vp_utils





# 역기구학 모듈
from ik_solver import KinematicsSolver

# SingleManipulator 모듈 설정
from omni.isaac.manipulators import SingleManipulator

# 오브젝트 조작 모듈
import omni.isaac.core.utils.xforms as xforms_utils

from omni.isaac.core.utils.rotations import quat_to_euler_angles, euler_angles_to_quat


class OgnMyIkExtensionPyInternalState:
    """Convenience class for maintaining per-node state information"""
    def __init__(self):
        self.initialized = None                                 # 초기화 여부 확인
        self.robot_prim_path = "/World/indy7"          # 로봇 경로
        self.tcp_prim_path = "/World/indy7/tcp/Cone"        # TCP 경로
        self.robot_name = "indy7"                      # 로봇 이름
        self.tcp_name = "tcp"                                   # TCP 이름
        self.state = "initial"                         # 초기 상태
        self.target_position = None                    # 목표 위치 저장
        self.target_orientation = None                 # 목표 방향 저장
        self.moving_position = np.array([
            [0.2763478696269433, 0.6613294271295742, 0.57414334622586574],
            [-0.2381942163216864, 0.6613294271295743, 0.57414334622586374],
            [0.28527684352036753, 0.6613294271295741, 0.6934492394294735],
            [-0.23819421632168628, 0.6613294271295741, 0.6934492394294734],
            [0.28527684352036753, 0.6613294271295741, 0.7934492394294735],
            [-0.23819421632168628, 0.6613294271295741, 0.7934492394294735],
            [0.28527684352036753, 0.6613294271295741, 0.9129736408124965],
            [-0.23819421632168628, 0.6613294271295741, 0.9129736408124965],
            [0.27527684352036753, 0.6613294271295741, 1.0323823700156143],
            [-0.23819421632168628, 0.6613294271295741, 1.0363234256728633]
            ])
        self.moving_orientation = np.array([0.0, 0.0, 1.0, 0.0])  # w, x, y, z quaternion
        self.current_position_index = 0  # 현재 위치 인덱스
        self.simulation_initialized = False             # 시뮬레이션 초기화 상태
        self.action_completed = True                   # 동작 완료 상태
        self.last_action_time = 0                      # 마지막 동작 시간
        self.action_delay = 1.0                        # 동작 간 지연 시간(초)
        self.cube_count = 1
        self.delta = None
        self.image_count = 0
        self.image_number = 0
        self.camera = True
        self.vp_utils = vp_utils  # vp_utils 모듈을 클래스 속성으로 추가
    def initialize_scene(self):
        self.scene = Scene()
        self.vp_utils.create_viewport_window(width=640,
                                height=640,
                                position_x=0,position_y=0,
                                camera_path="/World/Realsense/RSD455/Camera_OmniVision_OV9782_Color")
        
        
        # 로봇 매니퓰레이터 객체 초기화
        # prim_path: USD 씬 그래프 내 로봇의 경로
        # name: 로봇 식별자
        # end_effector_prim_name: 엔드이펙터(TCP) 이름
        self.manipulator = SingleManipulator(
            prim_path=self.robot_prim_path,
            name=self.robot_name,
            end_effector_prim_path="/World/indy7/tcp",  # 전체 TCP 경로를 직접 지정
            position = [0, 0, 0.5],
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
        self.my_controller.set_robot_base_pose(robot_positions=np.array([0.13703,0,0.7]), robot_orientation=np.array([1,0,0,0]))   
        
        # 로봇 객체의 관절 제어기 획득                 
        self.articulation_controller = self.my_robot.get_articulation_controller()  
        
        # 시뮬레이션이 시작될 때까지 대기
        while not self.simulation_initialized:
            try:
                # 로봇의 현재 상태를 확인하여 초기화 여부 테스트
                _ = self.my_robot.get_joint_positions()
                self.simulation_initialized = True
            except:
                time.sleep(0.1)  # 0.1초 대기
        
        self.initialized = True
        self.last_action_time = time.time()
        return
    
    # 시뮬레이션에서 정지 버튼을 누르면 반드시 한번 실행되는 함수
    def custom_reset(self):
        pass
    
    # reset 메서드 추가
    def reset(self):
        # 리소스 정리 및 초기화 로직
        self.initialized = None
        self.image_captured = False                    # 이미지 캡처 상태 초기화
        if hasattr(self, 'scene'):
            del self.scene
        if hasattr(self, 'manipulator'):
            del self.manipulator
        if hasattr(self, 'my_robot'):
            del self.my_robot
        if hasattr(self, 'my_controller'):
            del self.my_controller
        if hasattr(self, 'articulation_controller'):
            del self.articulation_controller
    
    def handle_initial_state(self):
        """Handle the initial state logic"""
        # cube_count가 5로 나누었을 때 3이면 cube_count를 증가시키고 패스
        if self.cube_count % 5 == 4:
            self.cube_count += 1
            self.state = "pick"
            return True

        if not self.action_completed:
            current_time = time.time()
            if current_time - self.last_action_time >= 2.0:  # 2초 대기
                self.action_completed = True
                self.state = "pick"
                self.cube_count += 1
                return False
            action = ArticulationAction(joint_positions=[0, 0, 0, 0, 0, 0])
            self.articulation_controller.apply_action(action)

            return True
            
        return False
        
    def handle_pick_state(self):
        """Handle the pick state logic"""
        # cube_count가 5로 나누었을 때 3이 아닌 경우에만 동작하도록 수정
        if self.cube_count % 5 == 4:
            current_time = time.time()
            if not hasattr(self, 'pick_wait_start_time'):
                self.pick_wait_start_time = current_time
            elif current_time - self.pick_wait_start_time >= 3:  # 3초 대기
                self.state = "grab"
                self.camera = True
                delattr(self, 'pick_wait_start_time')  # 대기 시간 초기화
                return True
        
            return False

        if not self.simulation_initialized:
            return False
            
        # 동작 완료 상태가 아니면 아직 이전 동작이 진행 중
        if not self.action_completed:
            current_time = time.time()
            if current_time - self.last_action_time >= 7:  # 1.5초 대기
                self.action_completed = True
                self.state = "grab"
                self.last_action_time = time.time()
                # print("pick state: pick the cube")
                return True
            return False
            
        # Prim 경로 유효성 검사
        cube_path = f"/World/Cube_{self.cube_count}"
        if not prims_utils.is_prim_path_valid(cube_path):
            carb.log_warn(f"Cube prim path {cube_path} is not valid")
            return False
            
        if not prims_utils.is_prim_path_valid(self.tcp_prim_path):
            carb.log_warn(f"TCP prim path {self.tcp_prim_path} is not valid")
            return False
            
        # 목표 객체의 위치 및 방향 획득
        tip_position, tip_quaternion = xforms_utils.get_world_pose(self.tcp_prim_path)
        position, quaternion = xforms_utils.get_world_pose(cube_path)
        
        # 목표 위치 설정 (z축으로 0.1m 위로)
        position[0] = position[0] +0.1
        position[1] = position[1] +0.1
        position[2] = position[2] +0.1

        # 역기구학 계산 수행
        actions, succ = self.my_controller.compute_inverse_kinematics(
            target_position=np.array(position),
            target_orientation=np.array(quaternion),
            position_tolerance=1
        )
        
        if succ:
            self.camera = True
            self.articulation_controller.apply_action(actions)
            self.action_completed = False
            self.last_action_time = time.time()
        else:
            carb.log_warn(f"IK did not converge to a solution for target {position}. No action is being taken.")
        return False

    def handle_grab_state(self):
        """Handle the grab state logic"""
        # cube_count가 5로 나누었을 때 3이 아닌 경우에만 동작하도록 수정
        if self.cube_count % 5 == 4:
            self.state = "put"
            return True

        if not self.action_completed:
            current_time = time.time()
            if current_time - self.last_action_time >= self.action_delay:
                self.action_completed = True
                self.state = "moving"
                self.last_action_time = time.time()
            return False
            
        # print("Grab state: Moving the cube")
        # 여기에 grab 동작 구현
        prims_utils.move_prim(f"/World/Cube_{self.cube_count}", f"/World/indy7/tcp/Cube_{self.cube_count}")
        
        self.action_completed = False
        # self.last_action_time = time.time()
        return True

    def handle_moving_state(self):
        """Handle the moving state logic"""
        # cube_count가 5로 나누었을 때 3이 아닌 경우에만 동작하도록 수정
        if self.cube_count % 5 == 4:
            self.state = "put"
            return True

        if not self.simulation_initialized:
            return False
            
        if not self.action_completed:
            current_time = time.time()
            if current_time - self.last_action_time >= self.action_delay:
                self.action_completed = True
            return False
            
        # print("Moving state: Moving to target position")
        
        # 목표 객체의 위치 및 방향 획득
        tip_position, tip_quaternion = xforms_utils.get_world_pose(self.tcp_prim_path)
        position=self.moving_position[(self.cube_count-1)%10]
        quaternion=self.moving_orientation

        
        # 역기구학 계산 수행
        actions, succ = self.my_controller.compute_inverse_kinematics(
            target_position=np.array(position),
            target_orientation=np.array(quaternion),
            position_tolerance=1
        )
        
        if succ:
            current_time = time.time()
            self.articulation_controller.apply_action(actions)
            
            if current_time - self.last_action_time > 15:
                self.state = "put"  
                self.action_completed = False
                self.last_action_time = time.time()
            return True
        else:
            carb.log_warn(f"IK did not converge to a solution for target {position}. No action is being taken.")
        return False


    def handle_put_state(self):
        # cube_count가 5로 나누었을 때 3이 아닌 경우에만 동작하도록 수정
        if self.cube_count % 5 == 4:
            self.state = "initial"
            return True

        current_time = time.time()
        if current_time - self.last_action_time >= 0.5:
            prims_utils.move_prim(f"/World/indy7/tcp/Cube_{self.cube_count}", f"/World/Cube_{self.cube_count}")
            self.state = "initial"
            
            return True
        return False
    
        
class OgnMyIkExtensionPy:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnMyIkExtensionPyInternalState()

    @staticmethod
    def compute(db) -> bool:
        csv_file_path = "C:/Users/user/Desktop/joint_torque.csv"

        """Compute the output based on inputs and internal state"""
        state = db.internal_state
        

            
        try:


            


            # db.inputs.input3가 0일 때 task를 실행, outputAttribute1이 1이 되면 멈춤
            # db.inputs.input3가 1이 들어오면 다시 task를 실행

            # 씬이 초기화되지 않았다면 초기화 수행
            if not state.initialized:
                state.initialize_scene()
                state.state = "pick"
                state.task_paused = False  # task 일시정지 상태 변수
            
            # task 일시정지 상태 변수 초기화
            if not hasattr(state, 'task_paused'):
                state.task_paused = False

            # if db.inputs.input4[0] < 0.4 and state.image_number < 5 and state.camera:
            #     try:
            #         # cube_count가 5로 나누었을 때 나머지가 3인 경우에도 이미지 캡처
            #         state.image_count += 1
            #         state.image_number += 1
            #         output_file_path = f"C:/isaacsim_4.2.0/intelligence/image_data/image{state.image_count}.png"
            #         activate = vp_utils.get_active_viewport()
            #         state.vp_utils.capture_viewport_to_file(activate, file_path=output_file_path)
            #         print(f"이미지 캡처 완료: {output_file_path}")
            #     except Exception as e:
            #         print(f"이미지 캡처 중 오류 발생: {str(e)}")
            # input3가 0일 때만 task 실행
            if db.inputs.input3 == 0 and db.outputs.outputAttribute1 == 0:
                state.task_paused = False

                # 상태에 따른 동작 수행
                if state.state == "pick":
                    if db.inputs.input4[0] < 0.4 and state.image_number < 5 and state.camera:
                        try:
                            # cube_count가 5로 나누었을 때 나머지가 3인 경우에도 이미지 캡처
                            state.image_count += 1
                            state.image_number += 1
                            output_file_path = f"C:/isaacsim_4.2.0/intelligence/vision_raw/image{state.image_count}.png"
                            activate = vp_utils.get_active_viewport()
                            state.vp_utils.capture_viewport_to_file(activate, file_path=output_file_path)
                            print(f"이미지 캡처 완료: {output_file_path}")
                            
                            if state.image_number == 5:
                                state.image_number = 0
                                state.camera = False
                        except Exception as e:
                            print(f"이미지 캡처 중 오류 발생: {str(e)}")
                    return state.handle_pick_state()
                elif state.state == "grab":
                    return state.handle_grab_state()
                elif state.state == "moving":
                    return state.handle_moving_state()
                elif state.state == "put":
                    return state.handle_put_state()
                elif state.state == "initial":
                    result = state.handle_initial_state()
                    if state.cube_count % 5 == 1 and state.cube_count >=5:
                        db.outputs.outputAttribute1 = 1
                        state.task_paused = True  # task 일시정지
                        return True  # 멈춤
                    else:
                        db.outputs.outputAttribute1 = 0
                    return result
                # 컨베이어 벨트가 멈췄을 때 이미지 캡처 (최대 5개)



            # input3가 1로 바뀌면 task 재시작
            elif db.inputs.input3 == 1:
                if state.task_paused:
                    # task 재시작
                    state.task_paused = False
                    db.outputs.outputAttribute1 = 0  # 재시작 신호
                    # 상태에 따른 동작 수행
                    if state.state == "pick" :
                        if db.inputs.input4[0] < 0.4 and state.image_number < 5 and state.camera:
                            try:
                                # cube_count가 5로 나누었을 때 나머지가 3인 경우에도 이미지 캡처
                                state.image_count += 1
                                state.image_number += 1
                                output_file_path = f"C:/isaacsim_4.2.0/intelligence/vision_raw/image{state.image_count}.png"
                                activate = vp_utils.get_active_viewport()
                                state.vp_utils.capture_viewport_to_file(activate, file_path=output_file_path)
                                print(f"이미지 캡처 완료: {output_file_path}")
                                
                                if state.image_number == 5:
                                    state.image_number = 0
                                    state.camera = False
                            except Exception as e:
                                print(f"이미지 캡처 중 오류 발생: {str(e)}")
                        return state.handle_pick_state()
                    elif state.state == "grab":
                        return state.handle_grab_state()
                    elif state.state == "moving":
                        return state.handle_moving_state()
                    elif state.state == "put":
                        return state.handle_put_state()
                    elif state.state == "initial":
                        result = state.handle_initial_state()
                        return result
                else:
                    # 이미 실행 중이면 기존 로직 유지
                    if state.state == "pick" and db.inputs.input2 == 0:
                        return state.handle_pick_state()
                    elif state.state == "grab":
                        return state.handle_grab_state()
                    elif state.state == "moving":
                        return state.handle_moving_state()
                    elif state.state == "put":
                        return state.handle_put_state()
                    elif state.state == "initial":
                        result = state.handle_initial_state()
                        return result

            else:
                # input3가 0, 1이 아닐 때는 아무 동작도 하지 않음
                return True

            # 현재 속도를 past_velocity로 업데이트
            
            # print(f"past_velocity: {state.past_velocity}")


        except Exception as error:
            db.log_error(str(error))
            return False

        return True
    
    ######################### 노드 인스턴스 해제 및 리소스 정리 메서드 #########################
    @staticmethod
    def release_instance(node, graph_instance_id):
        """Release the node instance and clean up resources"""
        try:
            print('release_instance')
            
            # 노드의 내부 상태를 가져옴
            state = node.per_instance_internal_state
            
           
        except Exception as e:
            print(f"Error during release: {str(e)}")
            state = None
        
        if state is not None:
            print('state is not None reset')
            try:
                state.reset()
            except Exception as e:
                print(f"Error during state reset: {str(e)}")
            
        return True