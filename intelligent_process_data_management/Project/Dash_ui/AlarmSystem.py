from dash import html

class AlarmSystem:
    def __init__(self):
        self.thresholds = {
            'pressure_war': 250,  # Mpa
            'pressure_kill': 250,  # Mpa
            'speed_war': 80,    # mm/s
            'speed_kill': 90,    # mm/s
            'humidity_max': 60,   # %
            'humidity_min': 30,   # %
            'temperature_max': 25, # °C
            'temperature_min': 15, # °C
            'torque_war': 2.5,     # N·m
            'torque_kill': 2.5     # N·m
        }
        
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
                    src='/assets/warning.png',
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

    def check_values(self, latest_data):
        alerts = []
        
        if latest_data.get('pressure_Mpa', 0) > self.thresholds['pressure_war']:
            alerts.append("보압 주의!")

        if latest_data.get('pressure_Mpa', 0) > self.thresholds['pressure_kill']:
            alerts.append("보압 위험!")

        if latest_data.get('speed_mm_per_s', 0) > self.thresholds['speed_war']:
            alerts.append("사출 속도 주의!")

        if latest_data.get('speed_mm_per_s', 0) > self.thresholds['speed_kill']:
            alerts.append("사출 속도 위험!")
            
        if latest_data.get('humidity_percent', 0) > self.thresholds['humidity_max']:
            alerts.append("습도 초과!")

        if latest_data.get('humidity_percent', 0) < self.thresholds['humidity_min']:
            alerts.append("습도 미달!")
            
        if latest_data.get('temperature_c', 0) > self.thresholds['temperature_max']:
            alerts.append("온도 초과!")

        if latest_data.get('temperature_c', 0) > self.thresholds['temperature_min']:
            alerts.append("온도 미달!")
            
        for i in range(6):
            if latest_data.get(f'joint_{i}', 0) > self.thresholds['torque']:
                alerts.append(f"Joint {i} 토크 주의!")
                
        return alerts