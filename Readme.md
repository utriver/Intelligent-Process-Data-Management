# 플라스틱 사출공정 자동화 프로젝트

NVIDIA Isaac Sim을 활용하여 가상 공정 환경을 구축하고, 공정 지능화를 위한 데이터 분류 체계 및 이기종 데이터베이스(InfluxDB, MongoDB) 통합 관리 시스템을 설계함.

### 📝 프로젝트 개요 (Project Overview)

기존 플라스틱 사출 공정은 숙련공의 경험에 의존한 수동 설정으로 인해 약 10% 내외의 불량률이 발생하는 한계가 있음. 이를 해결하기 위해 지능화가 필요한 핵심 지표를 정의하고, 가상 환경(NVIDIA Isaac Sim)과 실제 센서 데이터를 통합 관리하는 실시간 관제 시스템을 개발하여 공정 최적화 및 품질 관리 효율을 극대화.

### 🛠 활용 기술 (Technical Stack)

- **Management & Analysis**: Industry Intelligence Research, Data Classification, Equipment Selection
- **Simulation & DB**: NVIDIA Isaac Sim, InfluxDB (Time-series), MongoDB (Log)
- **Hardware & Control**: Dynamixel Motor Control, Raspberry Pi, Sensor Integration
- **Visualization**: Plotly Dash, UI/UX Strategy for Monitoring Center

### 🚀 핵심 기여 사항 (Key Contributions)

**1. 공정 지능화 전략 수립 및 데이터 정의**

- **산업군 및 필요성 조사**: 제조 산업 내 지능화 도입 현황을 조사하고, 특히 변수가 많은 플라스틱 사출 공정에서 데이터 기반 지능화가 수율 향상에 필수적임을 분석함.
- **데이터 종류 정의 및 분류**: 지능화 구현을 위해 필요한 데이터를 정의하고, 성격에 따라 **실시간(시계열 데이터)** 및 비실시간(로그/이미지 데이터)으로 분류하여 관리 체계를 설계함.
    
    - **실시간 데이터**: 보압, 수지 온도, 사출 속도, 로봇 토크 (InfluxDB 관리)
    - **비실시간 데이터**: 완제품 영상, 원료 재고량, 작동 주기 (MongoDB/HDF5 관리)
- **인프라 장비 선정**: 실시간 데이터 수집 및 공정 제어를 위해 라즈베리 파이, 다이나믹셀 모터, 온습도 센서 등 최적의 하드웨어 스펙을 선정함.

**2. 가상 공정(Digital Twin) 개발 및 데이터 파이프라인 구축**


- **가상 공정 시뮬레이션 개발**: **NVIDIA Isaac Sim**을 활용하여 사출기, 협동 로봇, 모바일 로봇(AMR)이 포함된 가상 사출 공정 환경을 구축함.
- **데이터 송출 시스템 구현**: 가상 공정 내에서 실시간으로 발생하는 로봇 조인트 토크 및 위치 데이터를 추출하여 **InfluxDB** 시계열 데이터베이스로 송출하는 파이프라인을 구축함.

**3. 스마트 팩토리 관제 UI 시각화 전략 수립**

- **사용자 경험 중심 시각화**: 운영자의 즉각적인 대응을 위해 데이터 특성별 시각화 전략을 제시함.
    
    
    - **직관성**: 보압 및 사출 속도를 계기판(Gauge) 형태로 표시하여 정상 범위를 즉시 파악하게 함.
    - **유효성**: 온습도 변화를 꺾은선 그래프로 표시하여 시계열 추이를 모니터링함.
    - **유연성**: 공정 오류 발생 시 수치 색상 변화 및 경고 알림 기능을 설계함.

**4. 하드웨어 제어 및 정밀 데이터 추출**

- **보압 데이터 추출을 위한 모터 제어**: 사출 공정의 핵심인 보압(Holding Pressure) 데이터를 물리적으로 구현하기 위해 **다이나믹셀 모터**의 전류 기반 토크 제어를 담당함.
- **실시간 물리량 계산**: 모터에 가해진 전류 값을 기반으로 압력과 스트로크 속도를 실시간으로 계산하는 알고리즘을 구현하여 현실 공정 데이터를 확보함.

$$
\tau = K_t \cdot I
$$

### 📈 주요 성과 (Key Results)

- **실시간 공정 가시성 및 모니터링 환경 구축**
    - 가상 및 현실 공정의 데이터를 통합하여 단일 대시보드(Dash)에서 관제 가능한 스마트 팩토리 기반을 마련함.
    - InfluxDB를 통해 10ms단위의 시계열 데이터를 지연 없이 처리하고 시각화함.
- **디지털 트윈을 통한 사전 검증**
    - 가상 공정에서 발생시킨 데이터를 활용해 실제 설비 도입 전 데이터 흐름 및 시각화 유효성을 성공적으로 검증함.


### 📗 폴더 설명
```
pressure setting: 현실 공정 세팅에 대한 파일(온습도, 보압, 사출속도)
intelligent_process_data_management: 데이터 베이스 세팅 관련 파일
IssacSim setting : 가상환경 세팅 관련 파일
```

### 💻 설치방법
### IsaacSim setting
**1. 가상환경 세팅**

- Isaac Sim 4.2.0 설치

- 압축 해제: C:/ 경로에 압축을 풉니다. (작성자 기준 경로: C:/isaacsim_4.2.0)

**2. Anaconda 가상환경 설정:**
```
conda create -n env_isaacsim python=3.10
conda activate env_isaacsim
cd C:\isaacsim_4.2.0
post_install.bat
isaac-sim.selector.bat
```
- 실행: Selector 창에서 START 버튼을 클릭하여 Isaac Sim을 실행합니다.

**3. 가상공정 세팅**

**a. 외부 파일 세팅**

압축 해제된 폴더 내의 파일들을 아래 경로에 맞춰 이동 및 교체합니다.

- IK Solver 설정: ik_solver.py 파일을 다음 경로로 이동

  - C:/isaacsim_4.2.0/kit/python/Lib

- Extensions 교체: exts.zip 파일을 다음 경로로 이동 후, 기존 exts 폴더를 삭제하고 압축 해제

  - C:/isaacsim_4.2.0/kit

- Intelligence 데이터: intelligence.zip 파일을 다음 경로로 이동 후 압축 해제

  - C:/isaacsim_4.2.0

**b. 가상환경 내부 설정 (Extensions)**

Isaac Sim 실행 후 상단 메뉴바에서 Window > Extensions로 이동하여 다음 설정을 진행합니다.

1. Conveyor 설정: conveyor 검색 후 아래 항목 활성화 (버전 확인 필수)

  - ISAACSIM CONVEYOR BELT UTILITY: v0.4.0

  - ISAACSIM CONVEYOR BELT UTILITY UI: v1.1.0

2. 필수 모듈 활성화: 아래 키워드를 각각 검색하여 모두 Enable 상태로 변경합니다.

- ik, mobility, mobility1, plastic, data_send

3. ActionGraph 확인:

- Window > Visual Scripting > ActionGraph 이동

- ogn 검색 후 상기 활성화한 5개 extension이 리스트에 있는지 확인합니다.

**c. 라이브러리 설치**

- 가상환경이 활성화된 터미널에서 아래 명령어를 입력하여 데이터베이스 연동 라이브러리를 설치합니다.

```
"C:\isaacsim_4.2.0\kit\python\python.exe" -m pip install influxdb
```
**4. 가상공정 실행**

1. 파일 로드: 상단 메뉴 File > Open 클릭

2. 경로 선택: ```C:\isaacsim_4.2.0\intelligence\ujin_isaacsim\indy7.usd``` 파일을 엽니다.

3. 시뮬레이션 시작: 왼쪽 툴바의 Play(실행) 버튼을 클릭하여 공정을 시작합니다.

### Pressure setting

**1. 환경 준비**

- Raspberry Pi: 전원을 켜고 인터넷 연결 상태를 확인합니다.

- DHT22 센서 연결:
  
  - GPIO 16번에 연결합니다.

  - 핀 구성: 3핀 (VCC, GND, Signal)

- Dynamixel XM430 연결:

  - USB 포트를 통해 연결합니다. (기본 경로: /dev/ttyUSB0)


**2. 필요한 패키지 설치**

터미널에서 아래 명령어를 순차적으로 실행하여 필요한 라이브러리를 설치합니다.

```
sudo apt-get update
sudo apt-get install python3-pip
pip3 install Adafruit_DHT influxdb dynamixel-sdk
```

**3. InfluxDB 서버 연결 정보 확인**

데이터 저장을 위한 서버 정보는 다음과 같습니다. 서버가 동작 중이어야 실시간 측정이 가능합니다.

|항목|정보|
|------------|-----------|
|**서버 주소**|172.18.73.63|
|**포트**|8086|
|**사용자명**|pi|
|**비밀번호**|simple2018|
|**데이터베이스**|solutionist|


**4. 코드 실행**

프로젝트 디렉토리에서 아래 명령어를 입력하여 메인 스크립트를 실행합니다.

```
python3 dy.py
```

**a. 실행 직후 자동 진행 작업:**

1. InfluxDB 체크: 서버 연결 및 DB 존재 여부 확인 후(없을 시 자동 생성).

2. DHT22 스레드: 온습도 실시간 측정 시작.

3. Dynamixel 스레드: 모터 각도 이동 및 전류·속도·압력 계산 시작.

4. 데이터 전송: 수집된 실시간 데이터를 InfluxDB로 전송 및 터미널 출력.

**5. 운영 중 상태 확인**
터미널에 출력되는 메시지를 통해 다음 사항을 모니터링할 수 있습니다.

- 센서 측정 데이터 값

- InfluxDB 서버 전송 성공 여부

**6. 종료 시 주의사항**
- 종료 방법: 터미널에서 Ctrl + C를 입력합니다.

- 안전 종료 절차:

  1. 🛑 통합 센서 시스템 종료 중... 메시지 출력 확인.

  2. 센서 스레드 안전 종료.

  3. Dynamixel 토크 해제 (하드웨어 보호).

  4. InfluxDB 연결 종료.