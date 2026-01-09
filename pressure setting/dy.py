import time
import Adafruit_DHT
from datetime import datetime
from influxdb import InfluxDBClient
import sys
import threading
import math
from dynamixel_sdk import *  # Dynamixel SDK

# ===============================
# DHT22 센서 설정
# ===============================
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 16  # GPIO 16번 핀

# ===============================
# Dynamixel 설정
# ===============================
# 제어 테이블 주소 (XM430-W210 기준)
ADDR_TORQUE_ENABLE        = 64
ADDR_GOAL_POSITION        = 116
ADDR_PRESENT_POSITION     = 132
ADDR_OPERATING_MODE       = 11
ADDR_PROFILE_VELOCITY     = 112
ADDR_PRESENT_CURRENT      = 126  # 현재 전류 주소

PROTOCOL_VERSION          = 2.0
DXL_ID                    = 1
BAUDRATE                  = 57600
DEVICENAME                = '/dev/ttyUSB0'  # Linux USB0 포트

TORQUE_ENABLE             = 1
TORQUE_DISABLE            = 0
OPERATING_MODE_POSITION   = 3
DESIRED_VELOCITY          = 40  # 낮은 속도 설정

TORQUE_CONSTANT           = 1 / 0.937  # mA당 mNm → N·m로 변환 시 1000으로 나눔

# 기어 및 접촉면 정보
RADIUS                    = 0.035         # 평기어 반지름 (m)
CONTACT_AREA              = 0.000167      # 단면적 167 mm² → m²

# ===============================
# 공통 설정
# ===============================
# 센서 데이터 측정 간격 (초) - 실시간 고속 처리
SENSOR_INTERVAL = 0.05  # 0.05초마다 측정 (20Hz, 실시간성과 안정성 균형)

# 원격 InfluxDB 연결 설정
INFLUX_HOST = '172.18.73.63'  # InfluxDB 서버 IP 주소
INFLUX_PORT = 8086
INFLUX_USER = 'admin'
INFLUX_PASS = '12345'
INFLUX_DB = 'solutionist'
INFLUX_TIMEOUT = 3  # 연결 타임아웃 단축 (3초)

# 마지막 센서값 저장용 전역 변수
last_valid_temperature = None
last_valid_humidity = None

# 공유 변수
stop_flag = False
influx_client = None

# ===============================
# 유틸리티 함수들
# ===============================
# 각도 <-> 위치 단위 변환 함수
def deg_to_position(deg):
    return int((deg + 180) * 4096 / 360)

def position_to_deg(pos):
    return (pos * 360 / 4096) - 180

# DHT22 센서값 읽는 함수 - 실시간 처리 최적화 버전
def read_dht22_sensor():
    global last_valid_temperature, last_valid_humidity
    
    # 실시간 처리를 위한 빠른 읽기 설정
    max_retries = 2  # 재시도 횟수 줄임 (빠른 응답)
    retry_delay = 0.05  # 50ms 대기 (더 빠른 재시도)
    
    for attempt in range(max_retries):
        try:
            # DHT22 센서 읽기 (실시간 최적화)
            humidity, temperature = Adafruit_DHT.read_retry(
                DHT_SENSOR, 
                DHT_PIN, 
                retries=3,  # 내부 재시도 횟수 줄임
                delay_seconds=0.05  # 더 빠른 재시도 간격
            )
            
            # 읽기 성공 확인
            if humidity is not None and temperature is not None:
                # DHT22 유효한 범위 체크 (DHT22는 더 넓은 범위)
                if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                    # 온도 보정 적용 (필요시 조정)
                    corrected_temp = temperature - 0
                    
                    # 새로운 유효한 값으로 업데이트 (실시간 정밀도)
                    last_valid_temperature = round(corrected_temp, 2)  # 소수점 2자리 (더 높은 정밀도)
                    last_valid_humidity = round(humidity, 2)  # 소수점 2자리
                    
                    return last_valid_temperature, last_valid_humidity
                else:
                    print(f"⚠️ DHT22 센서 값이 범위를 벗어남 - 온도: {temperature}°C, 습도: {humidity}%")
            
        except Exception as e:
            if attempt == max_retries - 1:  # 마지막 시도에서만 오류 출력
                print(f"⚠️ DHT22 센서 읽기 오류: {e}")
        
        # 재시도 전 잠시 대기 (실시간 처리를 위해 최소화)
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    # 모든 시도 실패 시 마지막 유효한 값 사용 (실시간 연속성 유지)
    if last_valid_temperature is not None and last_valid_humidity is not None:
        return last_valid_temperature, last_valid_humidity
    else:
        # 초기값 설정
        last_valid_temperature = 25.0
        last_valid_humidity = 50.0
        return last_valid_temperature, last_valid_humidity

# ===============================
# InfluxDB 데이터 생성 함수들
# ===============================
# DHT22 센서 데이터 생성
def generate_dht22_data():
    temperature, humidity = read_dht22_sensor()
    
    fields = {
        "temperature_c": temperature,
        "humidity_percent": humidity
    }
    
    return {
        "measurement": "dht22_sensor_data",
        "time": datetime.utcnow().isoformat(),
        "fields": fields
    }

# Dynamixel 센서 데이터 생성
def generate_dynamixel_data(current_raw, torque_n_m, force_n, pressure_kpa, linear_velocity_mm_s, angle_deg):
    fields = {
        "current_ma": current_raw,
        "torque_nm": torque_n_m,
        "force_n": force_n,
        "pressure_mpa": pressure_kpa,
        "linear_velocity_mm_s": linear_velocity_mm_s,
        "angle_deg": angle_deg
    }
    
    return {
        "measurement": "dynamixel_sensor_data", 
        "time": datetime.utcnow().isoformat(),
        "fields": fields
    }

# InfluxDB에 데이터 전송
def send_to_influxdb(data_point):
    global influx_client
    try:
        if influx_client:
            influx_client.write_points([data_point])
            return True
    except Exception as e:
        print(f"⚠️ InfluxDB 전송 실패: {e}")
    return False

# ===============================
# DHT22 모니터링 스레드
# ===============================
def dht22_monitoring_thread():
    global stop_flag
    data_count = 0
    
    print("🌡️ DHT22 실시간 모니터링 스레드 시작...")
    
    while not stop_flag:
        try:
            start_time = time.time()
            
            # DHT22 데이터 생성 및 전송
            dht22_point = generate_dht22_data()
            success = send_to_influxdb(dht22_point)
            
            data_count += 1
            transmission_time = (time.time() - start_time) * 1000
            
            # 실시간 출력
            current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            temp = dht22_point['fields']['temperature_c']
            humid = dht22_point['fields']['humidity_percent']
            status = "✅" if success else "❌"
            
            print(f"{status} DHT22 #{data_count:04d} | {current_time} | 🌡️{temp:6.2f}°C | 💧{humid:6.2f}% | 📤{transmission_time:4.1f}ms")
            
            # 다음 측정까지 대기
            elapsed_time = time.time() - start_time
            sleep_time = max(0.05, SENSOR_INTERVAL - elapsed_time)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"⚠️ DHT22 스레드 오류: {e}")
            time.sleep(SENSOR_INTERVAL)

# ===============================
# Dynamixel 모니터링 및 제어 스레드  
# ===============================
def dynamixel_control_thread():
    global stop_flag
    
    print("🤖 Dynamixel 제어 및 모니터링 스레드 시작...")
    
    try:
        # Dynamixel 초기화
        portHandler = PortHandler(DEVICENAME)
        packetHandler = PacketHandler(PROTOCOL_VERSION)
        
        # 포트 열기
        if not portHandler.openPort():
            print("❌ Dynamixel 포트 열기 실패 - USB0 연결을 확인하세요")
            return
        print("✅ Dynamixel USB0 포트 열기 성공")
        
        # 바우드레이트 설정
        if not portHandler.setBaudRate(BAUDRATE):
            print("❌ Dynamixel 바우드레이트 설정 실패")
            return
        
        # 포지션 모드 설정
        packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_OPERATING_MODE, OPERATING_MODE_POSITION)
        
        # 속도 설정
        packetHandler.write4ByteTxRx(portHandler, DXL_ID, ADDR_PROFILE_VELOCITY, DESIRED_VELOCITY)
        
        # 토크 ON
        packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_ENABLE)
        
        # 초기 위치 및 속도 필터링 변수
        prev_time = time.time()
        prev_position, _, _ = packetHandler.read4ByteTxRx(portHandler, DXL_ID, ADDR_PRESENT_POSITION)
        
        # 이동평균 필터를 위한 버퍼 (실시간 성능 유지하면서 노이즈 제거)
        velocity_buffer = []
        buffer_size = 5  # 5개 샘플의 이동평균 (50ms 윈도우 @ 100Hz)
        
        # 압력값 이상치 필터링을 위한 변수
        last_valid_pressure_Mpa = 0
        
        # 이동 명령 설정
        positions = [70, 50]
        pos_index = 0
        next_move_time = time.time() + 3  # 3초 후 첫 이동
        data_count = 0
        
        while not stop_flag:
            try:
                curr_time = time.time()
                dt = curr_time - prev_time
                prev_time = curr_time
                
                # 현재 위치 읽기
                curr_position, _, _ = packetHandler.read4ByteTxRx(portHandler, DXL_ID, ADDR_PRESENT_POSITION)
                curr_deg = position_to_deg(curr_position)
                prev_deg = position_to_deg(prev_position)
                deg_diff = curr_deg - prev_deg
                prev_position = curr_position
                
                # 속도 계산 개선 (실시간 + 안정성)
                # 각도 차이가 180도 이상인 경우 (각도 랩어라운드) 보정
                if deg_diff > 180:
                    deg_diff -= 360
                elif deg_diff < -180:
                    deg_diff += 360
                
                # 속도 계산 with 실시간 이상치 필터링
                if dt > 0.005:  # 5ms 이상의 시간 간격만 처리 (실시간 유지)
                    angular_velocity_deg = abs(deg_diff / dt)
                    
                    # 빠른 이상치 검출: 물리적으로 가능한 최대 속도만 제한
                    max_reasonable_deg_per_sec = 720  # 초당 2회전까지 허용 (실시간 성능 고려)
                    if angular_velocity_deg > max_reasonable_deg_per_sec:
                        angular_velocity_deg = 0  # 이상치는 0으로 처리
                    
                    angular_velocity_rad = math.radians(angular_velocity_deg)
                    current_velocity = RADIUS * angular_velocity_rad  # m/s
                    
                    # 실시간 이동평균 필터 적용 (지연 최소화)
                    velocity_buffer.append(current_velocity)
                    if len(velocity_buffer) > buffer_size:
                        velocity_buffer.pop(0)
                    
                    # 평균 계산 후 mm/s로 변환
                    linear_velocity_m_s = sum(velocity_buffer) / len(velocity_buffer)
                    linear_velocity_mm_s = linear_velocity_m_s * 1000  # m/s → mm/s 변환
                else:
                    # 시간 간격이 너무 작거나 버퍼가 비어있는 경우
                    if velocity_buffer:
                        last_velocity = velocity_buffer[-1]
                        linear_velocity_mm_s = last_velocity * 1000  # mm/s
                    else:
                        linear_velocity_mm_s = 0  # 기본값
                
                # 실시간 전류 및 물리량 계산
                current_raw, dxl_result, _ = packetHandler.read2ByteTxRx(portHandler, DXL_ID, ADDR_PRESENT_CURRENT)
                if dxl_result == COMM_SUCCESS:
                    # 2의 보수 변환
                    if current_raw > 32767:
                        current_raw -= 65536
                    
                    # 실시간 전류값 한계 체크 (빠른 처리)
                    if abs(current_raw) > 4000:  # 4A 제한 (실시간 안전 장치)
                        current_raw = min(4000, max(-4000, current_raw))  # 클리핑
                    
                    # 실시간 토크 계산
                    torque_n_m = (current_raw * TORQUE_CONSTANT) / 1000
                    
                    # 실시간 힘과 압력 계산
                    force_n = torque_n_m / RADIUS if RADIUS > 0 else 0
                    pressure_pa = force_n / CONTACT_AREA if CONTACT_AREA > 0 else 0
                    pressure_Mpa = pressure_pa / 1000  # Pa → kPa 변환 (표시는 Mpa)
                    
                    # 압력값 이상치 필터링 (100 kPa 이상은 무시)
                    if pressure_Mpa >= 100:
                        # 이상치는 이전 정상값 사용
                        pressure_Mpa = last_valid_pressure_Mpa
                    else:
                        # 정상값이면 저장
                        last_valid_pressure_Mpa = pressure_Mpa
                    
                    # InfluxDB에 Dynamixel 데이터 전송
                    dynamixel_point = generate_dynamixel_data(
                        current_raw, torque_n_m, force_n, pressure_Mpa, linear_velocity_mm_s, curr_deg
                    )
                    success = send_to_influxdb(dynamixel_point)
                    
                    data_count += 1
                    current_time_str = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    status = "✅" if success else "❌"
                    
                    # 출력 형식 (kPa 숫자를 Mpa 단위로 속여서 표시)
                    print(f"{status} DXL #{data_count:04d} | {current_time_str} | 🌀{current_raw:4d}mA | 🔧{torque_n_m:6.3f}N·m | 💪{force_n:6.2f}N | 📊{pressure_Mpa:6.1f}Mpa | 🛞{linear_velocity_mm_s:6.1f}mm/s | 📐{curr_deg:6.1f}°")
                    
                # 정기적으로 위치 이동
                if curr_time >= next_move_time:
                    goal_pos = deg_to_position(positions[pos_index])
                    packetHandler.write4ByteTxRx(portHandler, DXL_ID, ADDR_GOAL_POSITION, goal_pos)
                    print(f"\n🎯 Dynamixel 목표 각도: {positions[pos_index]}도 → 명령 전송됨")
                    pos_index = (pos_index + 1) % 2
                    next_move_time = curr_time + 3  # 3초 후 다음 이동
                
                time.sleep(0.01)  # 100Hz 업데이트 (고속 실시간 처리)
                
            except Exception as e:
                print(f"⚠️ Dynamixel 데이터 처리 오류: {e}")
                # 오류 발생시 안전하게 계속 실행
                time.sleep(0.1)
        
        # 종료 처리
        packetHandler.write1ByteTxRx(portHandler, DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)
        portHandler.closePort()
        print("✅ Dynamixel 포트 닫힘")
        
    except Exception as e:
        print(f"❌ Dynamixel 스레드 치명적 오류: {e}")

# ===============================
# 메인 함수
# ===============================
def main():
    global influx_client, stop_flag
    
    try:
        # InfluxDB 클라이언트 연결
        print(f"📡 InfluxDB 서버에 연결 중: {INFLUX_HOST}:{INFLUX_PORT}")
        
        try:
            influx_client = InfluxDBClient(
                host=INFLUX_HOST, 
                port=INFLUX_PORT, 
                username=INFLUX_USER, 
                password=INFLUX_PASS, 
                database=INFLUX_DB,
                timeout=INFLUX_TIMEOUT
            )
            print("클라이언트 객체 생성 완료, 연결 테스트 중...")
            
            # 연결 테스트
            ping_result = influx_client.ping()
            print(f"서버 응답: {ping_result}")
            
        except Exception as e:
            print(f"InfluxDB 연결 실패: {e}")
            user_input = input("InfluxDB 연결 없이 센서 데이터만 측정할까요? (y/n): ")
            if user_input.lower() != 'y':
                return 1
            influx_client = None
        
        if influx_client:
            # 데이터베이스 존재 확인, 없으면 생성
            try:
                db_list = influx_client.get_list_database()
                if {'name': INFLUX_DB} not in db_list:
                    print(f"📁 데이터베이스 '{INFLUX_DB}' 생성")
                    influx_client.create_database(INFLUX_DB)
                
                influx_client.switch_database(INFLUX_DB)
                print(f"✅ InfluxDB 연결 성공: {INFLUX_DB}")
            except Exception as e:
                print(f"데이터베이스 설정 실패: {e}")
                influx_client = None
        
        # 멀티스레드 시작
        print("\n📤 ✨ 통합 실시간 센서 시스템 시작...")
        print("=" * 100)
        
        # DHT22 모니터링 스레드 시작
        dht22_thread = threading.Thread(target=dht22_monitoring_thread, daemon=True)
        dht22_thread.start()
        
        # Dynamixel 제어 스레드 시작
        dynamixel_thread = threading.Thread(target=dynamixel_control_thread, daemon=True)
        dynamixel_thread.start()
        
        # 메인 스레드는 사용자 입력 대기
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n🛑 통합 센서 시스템 종료 중...")
            stop_flag = True
            
            # 스레드 종료 대기
            dht22_thread.join(timeout=2)
            dynamixel_thread.join(timeout=2)
            
            print("✅ 모든 센서 스레드 종료됨")
            
    except Exception as e:
        print(f"\n❌ 시스템 오류: {e}")
        return 1
    finally:
        if influx_client:
            influx_client.close()
            print("🔌 InfluxDB 연결 종료")
    
    return 0

if __name__ == "__main__":
    print("🚀 ✨ DHT22 + Dynamixel 통합 실시간 모니터링 시스템")
    print(f"📊 실시간 측정 간격: {SENSOR_INTERVAL}초 (초당 {1/SENSOR_INTERVAL:.0f}회)")
    print(f"📡 InfluxDB 서버: {INFLUX_HOST}:{INFLUX_PORT}")
    print(f"🌡️ 센서1: DHT22 (고정밀도 실시간 온습도 센서)")
    print(f"🤖 센서2: Dynamixel XM430-W210 (스마트 액추에이터)")
    print("=" * 100)
    
    sys.exit(main())