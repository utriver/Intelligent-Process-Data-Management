import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from influxdb import InfluxDBClient
from ui_components import ClickToModal
from alarm_system import AlarmSystem

class DataFetcher:
    def __init__(self, host='172.18.73.63', port=8086, user='admin', pwd='12345', db='solutionist'):
        self.client = InfluxDBClient(host=host, port=port, username=user, password=pwd, database=db)
        self.measurements = ['joint_torque', 'robot_position','dht22_sensor_data', 'dynamixel_sensor_data', 'quality_count', 'test_1']

    def get_joint_torque(self, limit=10):
        #query = f"SELECT * FROM joint_torque ORDER BY time DESC LIMIT {limit}"
        query = f"SELECT * FROM test_1 ORDER BY time DESC LIMIT {limit}"
        points = list(self.client.query(query).get_points())
        if not points:
            return pd.DataFrame()
        df = pd.DataFrame(points[::-1])
        df['time'] = pd.to_datetime(df['time'], utc=True)
        return df
    
    def get_dht22_data(self, limit=10):
        query = f"SELECT * FROM dht22_sensor_data ORDER BY time DESC LIMIT {limit}"
        points = list(self.client.query(query).get_points())
        if not points:
            return pd.DataFrame()
        df = pd.DataFrame(points[::-1])
        df['time'] = pd.to_datetime(df['time'], utc=True)
        return df
    
    def get_dynamixel_data(self, limit=10):
        query = f"SELECT * FROM dynamixel_sensor_data ORDER BY time DESC LIMIT {limit}"
        points = list(self.client.query(query).get_points())
        if not points:
            return pd.DataFrame()
        df = pd.DataFrame(points[::-1])
        df['time'] = pd.to_datetime(df['time'], utc=True)
        return df
    
    def get_quality_count(self, limit=10):
        # 1) 최근 limit개 레코드 가져오기
        query = f"SELECT * FROM quality_count ORDER BY time DESC LIMIT {limit}"
        points = list(self.client.query(query).get_points())
        if not points:
            return {}

        # 2) DataFrame으로 변환하고, 시간 순(오래된→최신)으로 정렬
        df = pd.DataFrame(points)
        df = df.iloc[::-1].reset_index(drop=True)

        # 3) 누락된 값을 바로 이전 값으로 채우기
        df[['normal_count', 'defect_count']] = (
            df[['normal_count', 'defect_count']]
            .ffill()
        )
        # 4) 가장 마지막(최신) 행에서 값 추출
        latest = df.iloc[-1]
        return {
            'normal': int(latest['normal_count']),
            'defect': int(latest['defect_count'])
        }


class GaugeFactory:
    @staticmethod
    def create(title, value, suffix, axis_range, steps, threshold, unit_font=None):
        bar_color = '#fa0404' if title == 'Pressure' else 'red'

        indicator = go.Indicator(
            mode="gauge+number",
            value=value,
            number={'suffix': suffix, 'font': unit_font or {}},
            title={'text': f"<b>{title}</b>", 'font': {'size': 22}},
            gauge={
                'axis': {'range': axis_range, 'dtick': 25},
                'bar': {'color': bar_color, 'thickness': 0.2},
                'steps': steps,
                'threshold': threshold
            },
            domain={'x': [0,1], 'y': [0,1]}
        )
        fig = go.Figure(indicator)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font={'color': 'white', 'family': 'Orbitron'},
            margin=dict(t=0, b=0, l=0, r=0)
        )
        return fig

class DashboardApp:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.app = dash.Dash(__name__)
        self.common = {
            'template': 'plotly_white',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': 'white', 'size': 16},
            'margin': {'l': 0, 'r': 0, 't': 50, 'b': 0}
        }
        self.alarm_system = AlarmSystem()
        self.modals = self.create_modals()
        self.layout()
        self.callbacks()

    def create_modals(self):
        return {
            'pressure': ClickToModal(
                self.app, 'pressure-gauge',
                lambda: self.create_gauge_figure('pressure'),
                {'width': '300px', 'height': '300px'},
                self.common
            ),
            'speed': ClickToModal(
                self.app, 'speed-gauge',
                lambda: self.create_gauge_figure('speed'),
                {'width': '300px', 'height': '300px'},
                self.common
            ),
            'humidity': ClickToModal(
                self.app, 'line_humidity',
                self.create_humidity_figure,
                {'width': '350px', 'height': '300px'},
                self.common
            ),
            'temperature': ClickToModal(
                self.app, 'line_temperature',
                self.create_temperature_figure,
                {'width': '350px', 'height': '300px'},
                self.common
            ),
            'pie': ClickToModal(
                self.app, 'pie-chart',
                self.create_pie_figure,
                {'width': '450px', 'height': '350px'},
                self.common
            )
        }

    def layout(self):
        legend_items = []
        
        self.app.layout = html.Div(style={
            'width': '100vw', 'height': '100vh',
            'backgroundImage': 'url("/assets/factory_2.png")',
            'backgroundSize': 'cover', 'overflow': 'hidden'
        }, children=[
            html.Div([
                html.Img(src='/assets/logo.png', style={'height':'120px'}),
                html.H1('플라스틱 사출 공정 모니터링', style={'color':'white'})
            ], style={'display':'flex','alignItems':'center','padding':'10px'}),

            html.Div([
                *self.modals['pressure'].components(),
                *self.modals['speed'].components()
            ], style={
                'position':'absolute','top':'250px','left':'25px',
                'display':'flex','flexDirection':'column','gap':'20px',
                'padding':'20px','borderRadius':'10px'
            }),
            html.Div([
                html.Div('📍 모바일 로봇 실시간 위치', style={'color':'white','fontSize':20}),
                html.Div([html.Img(src='/assets/robot_2.png', style={'width':'500px'}), html.Div(id='robot-dot')],
                         style={'position':'relative'})
            ], style={'position':'absolute','bottom':'50px','right':'30px'}),

            html.Div(
                self.modals['pie'].components(),
                style={'position':'absolute','top':'100px','right':'30px'}
            ),

            html.Div([
                *self.modals['humidity'].components(),
                *self.modals['temperature'].components()
            ], style={'position':'absolute','top':'10px','left':'600px','display':'flex','gap':'20px'}),

            html.Div([
                html.H2('🦿 로봇 조인트 토크 모니터링', style={'color':'white'}),
                html.Div(legend_items, style={'marginBottom':'10px','display':'flex','alignItems':'center'}),
                html.Div(id='torque-table'),
            ], style={
                'position':'absolute','bottom':'50px','left':'1200px',
                'transform':'translateX(-50%)','backgroundColor':'rgba(0,0,0,0.6)',
                'padding':'15px','borderRadius':'10px'
            }),
            self.alarm_system.create_alarm_div(),
            dcc.Interval(id='update-interval', interval=250, n_intervals=0)
        ])

    def callbacks(self):
        @self.app.callback(
            [Output('pressure-gauge-modal-graph', 'figure', allow_duplicate=True), 
            Output('speed-gauge-modal-graph', 'figure', allow_duplicate=True),
            Output('robot-dot', 'style'),
            Output('line_humidity-modal-graph', 'figure', allow_duplicate=True),
            Output('torque-table', 'children'),
            Output('line_temperature-modal-graph', 'figure', allow_duplicate=True),
            Output('pie-chart-modal-graph', 'figure', allow_duplicate=True),
            Output('alarm-container', 'style'),
            Output('alarm-text', 'children')],
            [Input('update-interval', 'n_intervals')],
            prevent_initial_call=True
        )
        def update(n):
            # Get data from each source
            raw_df = self.fetcher.get_joint_torque()
            joint_cols = [f'joint_{i}' for i in range(6)]
            joint_df  = raw_df.dropna(subset=joint_cols)
            pos_df    = raw_df.dropna(subset=['x','y'])
            
            dht22_df = self.fetcher.get_dht22_data()
            dynamixel_df = self.fetcher.get_dynamixel_data()

            if joint_df.empty or pos_df.empty or dht22_df.empty or dynamixel_df.empty:
                empty = html.Div('데이터 없음', style={'color':'white'})
                return [go.Figure()] * 7 + [{'display': 'none'}, empty]

            latest_joint = joint_df.iloc[-1]
            latest_pos   = pos_df.iloc[-1]
            latest_dht22 = dht22_df.iloc[-1]
            latest_dynamixel = dynamixel_df.iloc[-1]

            # Prepare data for monitoring
            joints = [f'Joint {i}' for i in range(6)]
            values = [latest_joint[f'joint_{i}'] for i in range(6)]

            # Create torque monitoring figure
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(
                y=joints, 
                x=values, 
                orientation='h', 
                marker_color='#1f77b4', 
                width=0.3, 
                showlegend=False
            ))

            # Add annotations
            annotations = [
                dict(x=v, y=j, text=f"{v:.2f} N·m", 
                    xanchor='left', showarrow=False, font=dict(color='white'))
                for j, v in zip(joints, values)
            ]

            fig_t.update_layout(
                barmode='stack',
                yaxis={'autorange': 'reversed'},
                xaxis={'range': [0, 5], 'title': 'Torque (N·m)'},
                annotations=annotations,
                **self.common
            )

            # Create other components
            style_dot = {
                'position': 'absolute',
                'top': f"{-latest_pos['x']*36+231}px",
                'left': f"{-latest_pos['y']*28+368}px",
                'width': '10px', 'height': '10px',
                'backgroundColor': 'red', 'borderRadius': '50%'
            }

            # Prepare data for alarm system
            dynamixel_data = {
                'pressure_mpa': latest_dynamixel['pressure_mpa'],
                'linear_velocity_mm_s': latest_dynamixel['linear_velocity_mm_s']
            }
            joint_torque_data = {f'joint_{i}': latest_joint[f'joint_{i}'] for i in range(6)}
            alerts = self.alarm_system.check_values(latest_dht22, dynamixel_data, joint_torque_data)

            alarm_style = {
                'display': 'block' if alerts else 'none',
                'position': 'fixed',
                'top': '50%',
                'left': '50%',
                'transform': 'translate(-50%, -50%)',
                'backgroundColor': 'rgba(255, 0, 0, 0.9)',
                'padding': '20px',
                'borderRadius': '10px',
                'zIndex': '2000',
                'textAlign': 'center',
                'animation': 'blink 1s infinite',
                'whiteSpace': 'pre-line'
            }

            return (
                self.create_gauge_figure('pressure'),
                self.create_gauge_figure('speed'),
                style_dot,
                self.create_humidity_figure(),
                dcc.Graph(figure=fig_t, config={'displayModeBar': False}),
                self.create_temperature_figure(),
                self.create_pie_figure(),
                alarm_style,
                '\n'.join(alerts)
            )
        
    def create_gauge_figure(self, gauge_type):
        dynamixel_df = self.fetcher.get_dynamixel_data()
        if dynamixel_df.empty:
            return go.Figure()
            
        latest = dynamixel_df.iloc[-1]
        if gauge_type == 'pressure':
            return GaugeFactory.create(
                '⬇️ Pressure', latest['pressure_mpa'], ' Mpa', [0,100],
                [{'range':[0,80],'color':'#1effa3'}, 
                {'range':[80,90],'color':'#ffee58'}, 
                {'range':[90,100],'color':'#ff5e5e'}],
                {'value':90,'line':{'color':'red','width':4}}
            )
        else:
            return GaugeFactory.create(
                '🔩 Injection Speed', latest['linear_velocity_mm_s'], ' mm/s', [0,100],
                [{'range':[0,80],'color':"#020303"}, 
                {'range':[80,90],'color':'#ffff66'}, 
                {'range':[90,100],'color':'#ff6666'}],
                {'value':90,'line':{'color':'red','width':4}}
            )

    def create_humidity_figure(self):
        dht22_df = self.fetcher.get_dht22_data()
        if dht22_df.empty:
            return go.Figure()
            
        fig = go.Figure(go.Scatter(
            x=dht22_df['time'], 
            y=dht22_df['humidity_percent'],
            mode='lines+markers', 
            name='습도 (%)',
            line=dict(color='blue')
        ))
        fig.update_layout(title='💧 원재료 보관소 습도', title_x=0.5, **self.common)
        return fig


    def create_temperature_figure(self):
        dht22_df = self.fetcher.get_dht22_data()
        if dht22_df.empty:
            return go.Figure()
            
        fig = go.Figure(go.Scatter(
            x=dht22_df['time'], 
            y=dht22_df['temperature_c'],
            mode='lines+markers', 
            name='온도 (°C)',
            line=dict(color='red')
        ))
        fig.update_layout(title='🌡️ 온도', title_x=0.5, **self.common)
        return fig

    def create_pie_figure(self):
        quality_data = self.fetcher.get_quality_count()
        total = quality_data['normal'] + quality_data['defect']
        
        fig = go.Figure(go.Pie(
            labels=['정상', '불량'],
            values=[quality_data['normal'], quality_data['defect']],
            marker=dict(colors=["#2ecc71", '#e74c3c']),
            textinfo='label+percent',
            hole=.3
        ))
        fig.update_layout(
            title=f'📊 생산품 품질 현황 (총 {total:,}개)', 
            title_x=0.5, 
            **self.common
        )
        return fig

    def run(self):
        self.app.run(debug=True, port=8050)

if __name__ == '__main__':
    DashboardApp().run()