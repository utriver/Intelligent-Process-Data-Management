"""
OmniGraph core Python API:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph/latest/Overview.html

OmniGraph attribute data types:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/dev/ogn/attribute_types.html

Collection of OmniGraph code examples in Python:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/dev/ogn/ogn_code_samples_python.html

Collection of OmniGraph tutorials:
  https://docs.omniverse.nvidia.com/kit/docs/omni.graph.tutorials/latest/Overview.html
"""
from omni.isaac.core.articulations import Articulation
from omni.isaac.core.utils.types import ArticulationActions
from omni.isaac.core.objects import DynamicCuboid
from omni.isaac.sensor import RotatingLidarPhysX
import numpy as np
from omni.isaac.core import SimulationContext
from influxdb import InfluxDBClient
from omni.isaac.core.articulations import Articulation
from datetime import datetime
import time

class OgnPlasticInjectionPyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.status = False
        self.prim_path="/World/Assem1_STEP_01"
        self.articulation = Articulation(prim_path=self.prim_path,position=np.array([-3.9520189076606633, -0.10730653983025275, 0.3]))
        self.max_position=0.6
        self.min_position=-0.15
        # Initialize the articulation immediately
        self.articulation.initialize()
        # Add movement control variables
        self.current_position = self.min_position
        self.target_position = self.max_position  # Start with max as target
        self.movement_step = 0.005  # units per frame
        self.frame_count = 0
        self.moving_to_max = True  # Track movement direction
        self.is_waiting_at_min = False  # Track if we're in delay state at min
        self.is_waiting_at_max = False  # Track if we're in delay state at max
        self.wait_start_frame = 0  # Frame when we started waiting
        self.wait_duration_frames_min = 120  # 4 seconds at 60 fps
        self.wait_duration_frames_max = 120 # 3 seconds at 60 fps
        self.cube_count = 0
        self.should_generate_cube = False  # Flag to track when to generate cube
        self.lidar=RotatingLidarPhysX(prim_path="/World/Lidar")
        self.pause_start_frame = 0  # 일시 정지 시작 프레임
        self.is_paused = False  # 일시 정지 상태 플래그
        self.normal_count = 0
        self.defect_count = 0
        self.IP_address = "172.18.73.63"
        self.client = InfluxDBClient(host=self.IP_address, port=8086, username="admin", password="12345", database="solutionist")

    def initialize_scene(self):
        """This method is kept for compatibility but initialization is done in __init__"""
        self.lidar.initialize()
        

    def move_to_position(self):
        """최대/최소 위치에서 딜레이를 두고 부드럽게 이동"""
        self.frame_count += 1

        # 일시 정지 상태 체크
        if self.is_paused:
            if self.frame_count - self.pause_start_frame >= 100:  # 5초 = 300 프레임
                self.is_paused = False
            return self.current_position

        # min 위치에서 대기 중일 때
        if self.is_waiting_at_min:
            if self.frame_count - self.wait_start_frame >= self.wait_duration_frames_min:
                self.is_waiting_at_min = False

                # cube_count가 10 이상이고, 10로 나눴을 때 나머지가 0이면 5초(=300프레임)간 정지
                # 단, pause_for_cube_count_1_once가 False일 때만 일시정지
                if (
                    self.cube_count >= 5
                    and self.cube_count % 5 == 0
                    and not hasattr(self, "pause_for_cube_count_1_once")
                ):
                    self.is_paused = True
                    self.pause_start_frame = self.frame_count
                    self.pause_for_cube_count_1_once = True  # 한 번만 일시정지
                else:
                    self.target_position = self.max_position
                    self.moving_to_max = True
            return self.current_position

        # max 위치에서 대기 중일 때
        if self.is_waiting_at_max:
            if self.frame_count - self.wait_start_frame >= self.wait_duration_frames_max:
                self.is_waiting_at_max = False
                self.target_position = self.min_position
                self.moving_to_max = False
            return self.current_position
        
        # 목표 위치로 이동
        if abs(self.current_position - self.target_position) > self.movement_step:
            if self.current_position < self.target_position:
                self.current_position += self.movement_step
            else:
                self.current_position -= self.movement_step
        else:
            # 목표 도달 시 타겟 전환
            self.current_position = self.target_position
            if self.moving_to_max:
                # max 위치에서 대기 시작
                self.is_waiting_at_max = True
                self.wait_start_frame = self.frame_count
            else:
                # min 위치 도달 시 큐브 생성 플래그
                self.should_generate_cube = True
                self.is_waiting_at_min = True
                self.wait_start_frame = self.frame_count

        return self.current_position

    def generate_cube(self):
        """
        cube_count가 10 이상이고 10로 나누었을 때 나머지가 0이면
        단 한 번만 cube_count를 증가시키지 않고, 그 이후에는 정상적으로 증가
        또한, cube_count가 5로 나누었을 때 나머지가 3이면 빨간색 큐브를 생성한다.
        """
        # pause_for_cube_count_1_once가 없으면(즉, 아직 1회 스킵 안 했으면) 1회만 스킵
        if (
            self.cube_count >= 5
            and self.cube_count % 5 == 0
            and not hasattr(self, "skip_cube_count_1_once")
        ):
            self.skip_cube_count_1_once = True  # 한 번만 스킵
            return  # 아무것도 하지 않고 함수 종료

        self.cube_count += 1

        # cube_count가 5로 나누었을 때 나머지가 3이면 빨간색, 아니면 흰색
        if self.cube_count % 5 == 4:
            color = np.array([1.0, 0.0, 0.0])  # 빨간색
            self.defect_count+=1
            print(self.defect_count)
        else:
            color = np.array([1.0, 1.0, 1.0])  # 흰색
            self.normal_count+=1
            print(self.normal_count)


        prim = DynamicCuboid( 
            prim_path=f"/World/Cube_{self.cube_count}",  # Unique name for each cube
            color=color,     # 색상 (RGB)
            mass=1.0,                            # 질량 (kg)
            scale=np.array([0.5, 0.4, 0.1]), 
            position=np.array([-3.012061739525756, -0.86113, 0.44829]),
            orientation=np.array([0, 0, 1, 0])     # 회전 (X, Y, Z, W)
        )
        

        
class OgnPlasticInjectionPy:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnPlasticInjectionPyInternalState()

    @staticmethod
    def compute(db) -> bool:
        """Compute the output based on inputs and internal state"""
        state = db.internal_state 

        try:
            simulation_context = SimulationContext()
            simulation_context.play()
            # print(db.inputs.inputAttribute2)
            # cube_count가 5로 나누었을 때 나머지가 3이면 inputAttribute2[0] 값과 상관없이 1.2 할당
            if state.cube_count % 5 == 4:
                db.outputs.outputAttribute1 = 1.2
            elif db.inputs.inputAttribute2[0] < 0.3:
                db.outputs.outputAttribute1 = 0
                # print("outputAttribute2=0")
            else: 
                db.outputs.outputAttribute1 = 1.2
                # print("outputAttribute2=2")
            # -----------------
            # Move to target position
            current_pos = state.move_to_position()
            
            # Generate cube if flag is set and not paused
            if state.should_generate_cube and not state.is_paused:
                state.generate_cube()
                state.should_generate_cube = False  # Reset flag
            try:
                # # 이전 카운트 값 저장
                # prev_normal_count = state.normal_count
                # prev_defect_count = state.defect_count
                
                # # 현재 카운트 값이 이전 값과 다를 경우에만 데이터 전송
                # if prev_normal_count != state.normal_count or prev_defect_count != state.defect_count:
                point1 = {
                    "measurement": "quality_count",
                    "tags": {
                        "robot_id": "robot_01"
                    },
                    "time": datetime.utcnow().isoformat(),
                    "fields": {
                        "normal_count": int(state.normal_count),
                        "defect_count": int(state.defect_count)
                    }
                }
                # print(point1)
                state.client.write_points([point1])
            except Exception as e:
                print("None")

            


            
            # Apply the movement only if not paused
            if not state.is_paused:
                control_actions = ArticulationActions(joint_positions=current_pos)
                state.articulation._articulation_view.apply_action(control_actions)
            # -----------------
        except Exception as e:
            db.log_error(f"Computation error: {e}")
            return False
        return True
