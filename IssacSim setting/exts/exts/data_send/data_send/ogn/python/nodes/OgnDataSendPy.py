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
from influxdb import InfluxDBClient
from omni.isaac.core.articulations import Articulation
from datetime import datetime
import time


class OgnDataSendPyInternalState:
    """Convenience class for maintaining per-node state information"""

    def __init__(self):
        """Instantiate the per-node state information"""
        self.status = False
        self.IP_address = "172.18.73.63"
        self.client = InfluxDBClient(host=self.IP_address, port=8086, username="admin", password="12345", database="solutionist")
        self.mobile_path = "/World/transporter"
        self.transporter = Articulation(prim_path=self.mobile_path)
        self.robot_name = "indy7"
        self.robot_prim_path = "/World/indy7"          # 로봇 경로
        self.robot_torque=Articulation(prim_path=self.robot_prim_path, name=self.robot_name)


    def initialize_scene(self):  
        self.transporter.initialize()
        self.robot_torque.initialize()





class OgnDataSendPy:
    """The Ogn node class"""

    @staticmethod
    def internal_state():
        """Returns an object that contains per-node state information"""
        return OgnDataSendPyInternalState()

    @staticmethod
    def compute(db) -> bool:
        """Compute the output based on inputs and internal state"""
        state = db.internal_state

        try:
            state.transporter.initialize()
            state.robot_torque.initialize()
            # -----------------
            # read input values
            # 모바일 로봇의 현재 위치 (x, y, z)를 가져옴
            mobile_position, _ = state.transporter.get_world_pose()
            # print(mobile_position)
            # x, y 좌표를 클라이언트에 전송
            try:
                point_1 = {
                            "measurement": "test_1",
                            "tags": {
                                "robot_id": "robot_01"
                            },
                            "time": datetime.utcnow().isoformat() + "Z",
                            "fields": {
                                "y": float(mobile_position[1]),
                                "x": float(mobile_position[0])
                            }
                        }
                # print(point_1)
            except Exception as e:
                print(f"모바일 데이터 위치 송신 오류: {e}")

            # 올바르게 write_points 호출
            state.client.write_points([point_1])
            torques = state.robot_torque.get_measured_joint_efforts()
            # print(torques)
            # dict 포맷으로 변환
            point_2 = {
                "measurement": "test_1",
                "tags": {
                    "robot": "my_robot"
                },
                "fields": {
                    f"joint_{i}": float(val) for i, val in enumerate(torques)
                },
                "time": int(time.time() * 1e9)  # 나노초 단위로 현재 시간
            }
            state.client.write_points([point_2])

            # do custom computation
            state.status = True
            # ...
            # write output values
            db.outputs.outputAttribute1 = 0.0
            # -----------------
        except Exception as e:
            db.log_error(f"Computation error: {e}")
            return False
        return True
