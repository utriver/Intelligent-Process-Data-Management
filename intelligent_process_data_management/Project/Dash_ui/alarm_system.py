from dash import html
import pandas as pd

class AlarmSystem:
    def __init__(self):
        self.thresholds = {
            'pressure_war': 80,   # Mpa
            'pressure_kill': 90,  # Mpa
            'speed_war': 80,     # mm/s
            'speed_kill': 90,    # mm/s
            'humidity_max': 60,   # %
            'humidity_min': 30,   # %
            'temperature_max': 25, # °C
            'temperature_min': 15, # °C
        }
        # Alarm div의 스타일은 create_alarm_div 메서드에서 직접 정의되어 있으므로, 
        # 이곳에 별도로 self.style을 추가할 필요는 없습니다. 
        # intelligence.py에서 alarm_style 변수를 사용하고 있다면, 
        # 해당 변수를 alarm_system.create_alarm_div()의 결과로 초기화해야 합니다.
        
    def create_alarm_div(self):
        return html.Div(
            id='alarm-container',
            style={
                'display': 'none',
                'position': 'fixed',
                'top': '50%',
                'left': '50%',
                'transform': 'translate(-50%, -50%)',
                'backgroundColor': 'rgba(255, 0, 0, 0.9)',
                'padding': '20px',
                'borderRadius': '10px',
                'zIndex': '2000',
                'textAlign': 'center',
                'animation': 'blink 1s infinite'
            },
            children=[
                html.Img(
                    src='/assets/emergency.jpg',  # 상대 경로를 Dash assets 폴더 기준으로 변경
                    style={'width': '100px', 'marginBottom': '10px'}
                ),
                html.Div(
                    id='alarm-text',
                    style={
                        'color': 'white',
                        'fontSize': '24px',
                        'fontWeight': 'bold'
                    }
                )
            ]
        )
    def check_values(self, dht_data, dynamixel_data, joint_torque_data):
        alerts = []
        
        # DHT22 센서 데이터 처리 (온습도)
        if isinstance(dht_data, pd.Series):
            try:
                humidity = float(dht_data['humidity_percent']) if 'humidity_percent' in dht_data else 0.0
                temperature = float(dht_data['temperature_c']) if 'temperature_c' in dht_data else 0.0
                
                if humidity > self.thresholds['humidity_max']:
                    alerts.append(f"⚠️ 습도 초과! ({humidity:.1f}% > {self.thresholds['humidity_max']}%)")
                if humidity < self.thresholds['humidity_min']:
                    alerts.append(f"⚠️ 습도 미달! ({humidity:.1f}% < {self.thresholds['humidity_min']}%)")

                if temperature > self.thresholds['temperature_max']:
                    alerts.append(f"🔴 온도 초과! ({temperature:.1f}°C > {self.thresholds['temperature_max']}°C)")
                if temperature < self.thresholds['temperature_min']:
                    alerts.append(f"🔴 온도 미달! ({temperature:.1f}°C < {self.thresholds['temperature_min']}°C)")
            except Exception as e:
                print(f"DHT22 데이터 처리 중 오류 발생: {e}")

        # 다이나믹셀 센서 데이터 처리 (압력, 속도)
        if isinstance(dynamixel_data, dict):
            try:
                pressure = float(dynamixel_data.get('pressure_mpa', 0))
                speed = float(dynamixel_data.get('linear_velocity_mm_s', 0))
                
                if pressure > self.thresholds['pressure_kill']:
                    alerts.append(f"🔴 보압 위험! ({pressure:.1f} Mpa > {self.thresholds['pressure_kill']} Mpa)")
                elif pressure > self.thresholds['pressure_war']:
                    alerts.append(f"🟡 보압 주의! ({pressure:.1f} Mpa > {self.thresholds['pressure_war']} Mpa)")

                if speed > self.thresholds['speed_kill']:
                    alerts.append(f"🔴 사출 속도 위험! ({speed:.1f} mm/s > {self.thresholds['speed_kill']} mm/s)")
                elif speed > self.thresholds['speed_war']:
                    alerts.append(f"🟡 사출 속도 주의! ({speed:.1f} mm/s > {self.thresholds['speed_war']} mm/s)")
            except Exception as e:
                print(f"다이나믹셀 데이터 처리 중 오류 발생: {e}")

        return alerts