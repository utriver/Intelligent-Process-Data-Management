import random
import time
from datetime import datetime
from influxdb import InfluxDBClient
import threading

# InfluxDB 연결 설정
client = InfluxDBClient(host='localhost', port=8086, username='admin', password='12345', database='solutionist')

robot_cycle = 0
finished_count = 0
quality_count = {'normal': 0, 'defect': 0}
quality_counter = 0

# 각 센서별 데이터 생성 함수
def get_temperature():
    return round(random.uniform(200, 300), 2)

def get_pressure():
    return round(random.uniform(50, 150), 2)

def get_speed():
    return round(random.uniform(20, 100), 2)

def get_robot_position():
    # x, y 좌표는 0~10 사이의 값으로 생성
    return round(random.uniform(0, 0), 2), round(random.uniform(0, 0), 2)

def get_humidity():
    return round(random.uniform(30, 70), 2)

def get_joint_torques():
    return {
        "joint_0": round(random.uniform(1.0, 5.0), 2),
        "joint_1": round(random.uniform(1.0, 5.0), 2),
        "joint_2": round(random.uniform(1.0, 5.0), 2),
        "joint_3": round(random.uniform(1.0, 5.0), 2),
        "joint_4": round(random.uniform(1.0, 5.0), 2),
        "joint_5": round(random.uniform(1.0, 5.0), 2),
    }

def generate_quality_data():
    """품질 데이터 생성 (10:1 비율로 정상:불량)"""
    global quality_count, quality_counter
    
    quality_counter += 1
    if quality_counter % 11 == 0:  # 11번째마다 불량품
        quality_count['defect'] += 1
        current_quality = 'defect'
    else:
        quality_count['normal'] += 1
        current_quality = 'normal'
    
    return {
        "measurement": "quality_count",
        "time": datetime.utcnow().isoformat(),
        "fields": {
            "normal_count": quality_count['normal'],
            "defect_count": quality_count['defect'],
            "current_quality": current_quality
        }
    }

# 측정값별 데이터 구성 함수
def generate_dht_dynamixel_data():
    """DHT 센서 및 다이나믹셀 센서 데이터를 포함하는 측정값"""
    fields = {
        #"temperature_c": get_temperature(),
        "pressure_mpa": get_pressure(),
        "linear_velocity_mm_s": get_speed(),
        #"humidity_percent": get_humidity(),
    }
    return {
        "measurement": "test_1",
        "time": datetime.utcnow().isoformat(),
        "fields": fields
    }

def generate_robot_data():
    pos_x, pos_y = get_robot_position()
    joint_torques = get_joint_torques()

    fields = {
        "x": pos_x,
        "y": pos_y,
        **joint_torques, # 조인트 토크 필드들 추가
    }
    return {
        "measurement": "joint_torque",
        "time": datetime.utcnow().isoformat(),
        "fields": fields
    }

# --- 스레드별 작업 함수 ---
def send_dht_dynamixel_data():
    """DHT 센서 및 다이나믹셀 데이터를 1초 간격으로 전송하는 스레드"""
    while True:
        point = generate_dht_dynamixel_data()
        try:
            client.write_points([point])
            print(f"✅ [DHT/Dynamixel] 전송됨: measurement = {point['measurement']}, Temp={point['fields']['temperature_c']:.2f}, Pressure={point['fields']['pressure_pa']:.2f}")
        except Exception as e:
            print(f"❗️ [DHT/Dynamixel] 전송 실패: {e}")
        time.sleep(1) # 1초 간격으로 전송

def send_robot_data():
    """로봇 관련 데이터를 0.5초 간격으로 전송하는 스레드"""
    while True:
        point = generate_robot_data()
        try:
            client.write_points([point])
            print(f"✅ [Robot Data] 전송됨: measurement = {point['measurement']}, Pos=({point['fields']['x']:.2f}, {point['fields']['y']:.2f})")
        except Exception as e:
            print(f"❗️ [Robot Data] 전송 실패: {e}")
        time.sleep(0.1)

def send_quality_data():
    """품질 데이터를 2초 간격으로 전송하는 스레드"""
    while True:
        point = generate_quality_data()
        try:
            client.write_points([point])
            print(f"✅ [Quality] 전송됨: 정상={point['fields']['normal_count']}, 불량={point['fields']['defect_count']}")
        except Exception as e:
            print(f"❗️ [Quality] 전송 실패: {e}")
        time.sleep(1)  # 2초 간격으로 전송

print("\n📤 실시간 센서 데이터 전송 시작... (종료: Ctrl + C)\n")

if __name__ == "__main__":
    # 각 작업을 수행할 스레드 생성
    thread_dht_dynamixel = threading.Thread(target=send_dht_dynamixel_data)
    thread_robot_data = threading.Thread(target=send_robot_data)
    thread_quality = threading.Thread(target=send_quality_data)

    # 스레드를 데몬으로 설정하여 메인 프로그램 종료 시 함께 종료되도록 함
    thread_dht_dynamixel.daemon = True
    thread_robot_data.daemon = True
    thread_quality.daemon = True

    print("\n📤 실시간 센서 데이터 전송 시작... (종료: Ctrl + C)\n")

    # 스레드 시작
    #thread_dht_dynamixel.start()
    thread_quality.start()
    thread_robot_data.start()

    try:
        # KeyboardInterrupt를 받기 위해 메인 스레드가 대기
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 센서 시뮬레이션 종료됨.")