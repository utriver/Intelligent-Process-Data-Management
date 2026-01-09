# -*- coding: utf-8 -*-
# integrated_dashboard_v2.py - 스트리밍 배경 + 스마트 팩토리 대시보드 통합 (에러 처리 강화)
import os
import sys
import socket
import traceback

# 한글 컴퓨터명 문제 해결
os.environ['PYTHONIOENCODING'] = 'utf-8'
original_getfqdn = socket.getfqdn
def patched_getfqdn(name=''):
    try:
        return original_getfqdn(name)
    except UnicodeDecodeError:
        return '172.18.73.63'
socket.getfqdn = patched_getfqdn

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import random
from pymongo import MongoClient
from influxdb import InfluxDBClient

print("🔧 데이터베이스 연결 시도...")

# 데이터베이스 연결 (에러 처리 강화)
mongo_client = None
influx_client = None

try:
    mongo_client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    # 연결 테스트
    mongo_client.admin.command('ping')
    mongo_db = mongo_client["smart_factory_db"]
    print("✅ MongoDB 연결 성공")
except Exception as e:
    print(f"❌ MongoDB 연결 실패: {e}")
    mongo_client = None
    mongo_db = None

try:
    influx_client = InfluxDBClient(
        host='localhost', 
        port=8086, 
        username='admin', 
        password='12345', 
        database='solutionist',
        timeout=3
    )
    # 연결 테스트
    influx_client.ping()
    print("✅ InfluxDB 연결 성공")
except Exception as e:
    print(f"❌ InfluxDB 연결 실패: {e}")
    influx_client = None

def get_latest_factory_data():
    """InfluxDB에서 최신 팩토리 데이터 가져오기 (에러 처리 강화)"""
    try:
        if not influx_client:
            print("❌ InfluxDB 클라이언트가 없습니다. 더미 데이터를 반환합니다.")
            return create_dummy_data()
        
        measurements = ['joint_torque', 'dht11_sensor_data', 'factory_data']
        dfs = []
        
        for m in measurements:
            try:
                query = f'SELECT * FROM {m} ORDER BY time DESC LIMIT 20'
                result = influx_client.query(query)
                points = list(result.get_points())[::-1]
                
                if points:
                    df = pd.DataFrame(points)
                    df['time'] = pd.to_datetime(df['time'], utc=True, errors='coerce')
                    df['measurement'] = m
                    dfs.append(df)
                    print(f"✅ {m}: {len(points)}개 데이터 로드")
                else:
                    print(f"⚠️ {m}: 데이터 없음")
                    
            except Exception as e:
                print(f"❌ {m} 쿼리 오류: {e}")
                continue
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df = combined_df.sort_values(by='time')
            print(f"✅ 총 {len(combined_df)}개 통합 데이터 반환")
            return combined_df
        else:
            print("⚠️ 모든 measurement에서 데이터를 가져올 수 없습니다. 더미 데이터를 반환합니다.")
            return create_dummy_data()
            
    except Exception as e:
        print(f"❌ get_latest_factory_data 전체 오류: {e}")
        print(f"❌ 오류 상세: {traceback.format_exc()}")
        return create_dummy_data()

def create_dummy_data():
    """더미 데이터 생성"""
    print("🔄 더미 데이터 생성 중...")
    
    current_time = pd.Timestamp.now()
    time_points = [current_time - pd.Timedelta(minutes=i) for i in range(20, 0, -1)]
    
    dummy_data = []
    for i, time_point in enumerate(time_points):
        dummy_data.append({
            'time': time_point,
            'temperature_c': 220 + random.uniform(-5, 5),
            'pressure_bar': 150 + random.uniform(-10, 10),
            'speed_mm_per_s': 50 + random.uniform(-5, 5),
            'humidity_percent': 45 + random.uniform(-5, 5),
            'x': random.uniform(10, 40),
            'y': random.uniform(10, 30),
            'joint_0': random.uniform(0.5, 2.8),
            'joint_1': random.uniform(0.5, 2.8),
            'joint_2': random.uniform(0.5, 2.8),
            'joint_3': random.uniform(0.5, 2.8),
            'joint_4': random.uniform(0.5, 2.8),
            'joint_5': random.uniform(0.5, 2.8),
            'measurement': 'dummy_data'
        })
    
    df = pd.DataFrame(dummy_data)
    print(f"✅ 더미 데이터 {len(df)}개 생성 완료")
    return df

# Dash 앱 생성 (assets 폴더 활용)
app = dash.Dash(__name__, assets_folder='assets')

# 메타 태그 설정
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>스마트 팩토리 대시보드 with 실시간 스트리밍</title>
        {%favicon%}
        {%css%}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { margin: 0; padding: 0; overflow: hidden; }
            #react-entry-point { height: 100vh; position: relative; z-index: 10; }
            
            /* 스트리밍 로그 표시 */
            #streaming-log {
                position: fixed;
                top: 50px;
                right: 10px;
                width: 300px;
                max-height: 200px;
                background: rgba(0,0,0,0.9);
                color: #00ff00;
                padding: 10px;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                overflow-y: auto;
                z-index: 1000;
                display: none;
            }
            
            /* 토글 버튼 */
            #log-toggle {
                position: fixed;
                top: 10px;
                right: 320px;
                background: rgba(0,0,0,0.8);
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
                z-index: 1001;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <!-- 스트리밍 로그 토글 버튼 -->
        <button id="log-toggle" onclick="toggleStreamingLog()">📋 로그</button>
        
        <!-- 스트리밍 로그 영역 -->
        <div id="streaming-log">
            <div style="color: #ffff00; font-weight: bold;">🎥 스트리밍 로그</div>
            <div id="log-content">로그 대기 중...</div>
        </div>
        
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
            
            <script>
                // 스트리밍 로그 토글
                function toggleStreamingLog() {
                    const log = document.getElementById('streaming-log');
                    log.style.display = log.style.display === 'none' ? 'block' : 'none';
                }
                
                // 로그 추가 함수
                function addStreamingLog(message, type = 'info') {
                    const logContent = document.getElementById('log-content');
                    const timestamp = new Date().toLocaleTimeString();
                    const colors = {
                        'info': '#00bfff',
                        'success': '#00ff00',
                        'warning': '#ffaa00',
                        'error': '#ff4444'
                    };
                    
                    const logEntry = document.createElement('div');
                    logEntry.innerHTML = `<span style="color: #666;">[${timestamp}]</span> <span style="color: ${colors[type] || '#00bfff'};">${message}</span>`;
                    logContent.appendChild(logEntry);
                    
                    // 최대 50개 로그만 유지
                    while (logContent.children.length > 50) {
                        logContent.removeChild(logContent.firstChild);
                    }
                    
                    // 자동 스크롤
                    logContent.scrollTop = logContent.scrollHeight;
                }
                
                // 전역 로그 함수 등록
                window.addStreamingLog = addStreamingLog;
                
                // 초기 로그
                addStreamingLog('스트리밍 로그 시스템 초기화됨', 'success');
            </script>
        </footer>
    </body>
</html>
'''

# 임시 정적 데이터
df_weight = pd.DataFrame({'항목': ['청색', '적색', '노랑', '흑색'], '무게': [400, 300, 500, 600]})
df_production = pd.DataFrame({'날짜': pd.date_range('2025-04-01', periods=7),
                               '생산수량': [1500, 1800, 1700, 2000, 2100, 1950, 2200]})
df_defect = pd.DataFrame({'불량률': [0.02, 0.015, 0.018, 0.01, 0.012, 0.02, 0.017]})
df_dye = pd.DataFrame({'염료 종류': ['청색', '적색', '노랑', '흑색'], '재고량': [120, 80, 50, 30]})

# 색상 매핑
color_map = {'청색': '#1f77b4', '적색': '#d62728', '노랑': '#ffbf00', '흑색': '#2f2f2f'}
weight_color_map = color_map.copy()

# 공통 레이아웃
common_layout = dict(
    template='plotly_white',
    plot_bgcolor='rgba(255,255,255,0.1)',  # 반투명 배경
    paper_bgcolor='rgba(255,255,255,0.1)',  # 반투명 배경
    font=dict(color='white', size=16, family='Arial, sans-serif'),  # 흰색 텍스트
    margin=dict(l=0, r=0, t=50, b=0),
)

# 초기 그래프 생성
def create_line_humidity_figure(df):
    """습도 변화 그래프"""
    try:
        if df.empty or 'humidity_percent' not in df.columns:
            # 빈 그래프 반환
            fig = go.Figure()
            fig.add_annotation(
                text="습도 데이터 없음",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                font=dict(size=16, color="white"),
                showarrow=False
            )
        else:
            fig = go.Figure(go.Scatter(
                x=pd.to_datetime(df['time'], format='ISO8601'),
                y=df['humidity_percent'],
                mode='lines+markers',
                line=dict(color='cyan', width=3),
                marker=dict(size=8, color='cyan')
            ))
        
        fig.update_layout(
            title='원재료 보관소 습도 변화', 
            title_x=0.5,
            title_font=dict(color='white', size=18),
            **common_layout
        )
        return fig
    except Exception as e:
        print(f"❌ 습도 그래프 생성 오류: {e}")
        # 오류 시 빈 그래프 반환
        fig = go.Figure()
        fig.add_annotation(
            text=f"그래프 오류: {str(e)[:30]}...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            font=dict(size=14, color="red"),
            showarrow=False
        )
        fig.update_layout(**common_layout)
        return fig

# 초기 그래프들 (정적)
dummy_fig = go.Figure()
dummy_fig.update_layout(**common_layout)

# 염료 재고량 바 차트
bar_dye = go.Figure()
for _, row in df_dye.iterrows():
    bar_dye.add_trace(go.Bar(
        x=[row['염료 종류']], 
        y=[row['재고량']], 
        marker_color=color_map[row['염료 종류']],
        opacity=0.8
    ))
bar_dye.update_layout(
    title='원재료 무게 데이터', 
    title_x=0.5,
    title_font=dict(color='white', size=18),
    **common_layout, 
    showlegend=False
)

# 완제품 수량 파이 차트
pie_weight = go.Figure(go.Pie(
    labels=df_weight['항목'],
    values=df_weight['무게'],
    marker=dict(colors=[weight_color_map[c] for c in df_weight['항목']])
))
pie_weight.update_layout(
    title='완제품 수량 데이터',
    title_font=dict(color='white', size=18),
    **common_layout
)

# 앱 레이아웃 (스트리밍 배경 + 대시보드 오버레이)
app.layout = html.Div([
    # 스트리밍 배경을 위한 iframe
    html.Iframe(
        src='/assets/streaming.html',
        style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100vw',
            'height': '100vh',
            'border': 'none',
            'z-index': '0',
            'pointer-events': 'none'
        }
    ),
    
    # 메인 대시보드 컨테이너
    html.Div([
        # 헤더
        html.Div([
            html.Img(src='/assets/logo.png', style={'height': '120px'}),
            html.H1('플라스틱 사출 공정 모니터링', style={
                'color': 'white', 
                'textShadow': '2px 2px 4px rgba(0,0,0,0.8)',
                'fontSize': '32px'
            })
        ], style={
            'display': 'flex', 
            'alignItems': 'center', 
            'padding': '10px',
            'backgroundColor': 'rgba(0,0,0,0.6)',
            'backdropFilter': 'blur(5px)'
        }),

        # 센서 데이터 표시 영역
        html.Div([
            html.Div([
                html.H4('수지온도', style={'color': 'white'}),
                html.H2(id='temp-display', style={'color': '#00FFFF'})
            ], style={'marginBottom': '20px'}),
            html.Div([
                html.H4('보압', style={'color': 'white'}),
                html.H2(id='pressure-display', style={'color': '#00FF00'})
            ], style={'marginBottom': '20px'}),
            html.Div([
                html.H4('사출속도', style={'color': 'white'}),
                html.H2(id='speed-display', style={'color': '#FFA500'})
            ])
        ], style={
            'position': 'absolute', 
            'top': '250px', 
            'left': '200px',
            'backgroundColor': 'rgba(0,0,0,0.8)', 
            'padding': '20px', 
            'borderRadius': '10px',
            'backdropFilter': 'blur(10px)',
            'border': '1px solid rgba(255,255,255,0.2)'
        }),

        # 모바일 로봇 위치
        html.Div([
            html.Div('모바일 로봇 실시간 위치', style={
                'color': 'white', 
                'fontSize': '20px',
                'textShadow': '2px 2px 4px rgba(0,0,0,0.8)'
            }),
            html.Div([
                html.Img(src='/assets/robot.png', style={'width': '500px', 'opacity': '0.9'}),
                html.Div(id='robot-dot')
            ], style={'position': 'relative'})
        ], style={
            'position': 'absolute', 
            'bottom': '50px', 
            'right': '30px',
            'backgroundColor': 'rgba(0,0,0,0.6)',
            'padding': '15px',
            'borderRadius': '10px',
            'backdropFilter': 'blur(5px)'
        }),

        # 원재료 무게 차트
        html.Div([
            dcc.Graph(
                figure=bar_dye, 
                config={'displayModeBar': False}, 
                style={'width': '300px', 'height': '300px'}
            )
        ], style={
            'position': 'absolute', 
            'top': '60px', 
            'left': '1280px',
            'backgroundColor': 'rgba(0,0,0,0.7)',
            'borderRadius': '10px',
            'backdropFilter': 'blur(5px)'
        }),

        # 협동로봇 작동 주기
        html.Div([
            html.H4('협동로봇 작동 주기', style={'color': 'white'}),
            html.H2(id='cycle-count', style={'color': '#FFD700'})
        ], style={
            'position': 'absolute', 
            'bottom': '500px', 
            'left': '1250px',
            'backgroundColor': 'rgba(0,0,0,0.8)', 
            'padding': '10px', 
            'borderRadius': '10px',
            'backdropFilter': 'blur(10px)',
            'border': '1px solid rgba(255,255,255,0.2)'
        }),

        # 완제품 수량 파이 차트
        html.Div([
            dcc.Graph(
                figure=pie_weight, 
                config={'displayModeBar': False}, 
                style={'width': '450px', 'height': '350px'}
            )
        ], style={
            'position': 'absolute', 
            'top': '100px', 
            'right': '30px',
            'backgroundColor': 'rgba(0,0,0,0.7)',
            'borderRadius': '10px',
            'backdropFilter': 'blur(5px)'
        }),

        # 습도 변화 그래프
        html.Div([
            dcc.Graph(
                id='line_humidity', 
                figure=dummy_fig, 
                config={'displayModeBar': False}, 
                style={'width': '350px', 'height': '300px'}
            )
        ], style={
            'position': 'absolute', 
            'top': '10px', 
            'left': '600px',
            'backgroundColor': 'rgba(0,0,0,0.7)',
            'borderRadius': '10px',
            'backdropFilter': 'blur(5px)'
        }),

        # 로봇 조인트 토크 모니터링
        html.Div([
            html.H2("로봇 조인트 토크 모니터링", style={
                'color': 'white',
                'textShadow': '2px 2px 4px rgba(0,0,0,0.8)'
            }),

            html.Div([
                html.Span(style={
                    'display': 'inline-block',
                    'width': '12px',
                    'height': '12px',
                    'backgroundColor': 'lightgray',
                    'marginRight': '5px',
                    'borderRadius': '2px'
                }),
                html.Span("정상범위", style={'color': 'white', 'marginRight': '15px'}),

                html.Span(style={
                    'display': 'inline-block',
                    'width': '12px',
                    'height': '12px',
                    'backgroundColor': 'yellow',
                    'marginRight': '5px',
                    'borderRadius': '2px'
                }),
                html.Span("주의", style={'color': 'white', 'marginRight': '15px'}),

                html.Span(style={
                    'display': 'inline-block',
                    'width': '12px',
                    'height': '12px',
                    'backgroundColor': 'red',
                    'marginRight': '5px',
                    'borderRadius': '2px'
                }),
                html.Span("위험", style={'color': 'white'})
            ], style={'marginBottom': '10px', 'display': 'flex', 'alignItems': 'center'}),
            html.Div(id='torque-table')
        ], style={
            'position': 'absolute',
            'bottom': '50px',
            'left': '900px',
            'transform': 'translateX(-50%)',
            'backgroundColor': 'rgba(0,0,0,0.8)',
            'padding': '15px',
            'borderRadius': '10px',
            'fontFamily': 'Arial, sans-serif',
            'backdropFilter': 'blur(10px)',
            'border': '1px solid rgba(255,255,255,0.2)'
        }),

        # 데이터베이스 상태 표시
        html.Div([
            html.Div(f"DB: {'✅' if influx_client is not None else '❌'} InfluxDB | {'✅' if mongo_db is not None else '❌'} MongoDB", 
                    style={'color': 'white', 'fontSize': '12px'})
        ], style={
            'position': 'absolute',
            'bottom': '10px',
            'left': '10px',
            'backgroundColor': 'rgba(0,0,0,0.8)',
            'padding': '5px',
            'borderRadius': '5px'
        }),

        # 업데이트 인터벌
        dcc.Interval(id='update-interval', interval=1000, n_intervals=0)

    ], style={
        'position': 'relative',
        'width': '100vw', 
        'height': '100vh',
        'overflow': 'hidden',
        'zIndex': '10'
    })
], style={
    'margin': '0',
    'padding': '0',
    'height': '100vh',
    'overflow': 'hidden'
})

@app.callback(
    [Output('temp-display', 'children'),
     Output('pressure-display', 'children'),
     Output('speed-display', 'children'),
     Output('robot-dot', 'style'),
     Output('line_humidity', 'figure'),
     Output('torque-table', 'children'),
     Output('cycle-count', 'children')],
    Input('update-interval', 'n_intervals')
)
def update_sensor_display(n):
    """센서 데이터 업데이트 콜백 (에러 처리 강화)"""
    try:
        print(f"🔄 업데이트 #{n} 시작...")
        
        # 데이터 가져오기
        data = get_latest_factory_data()
        if data is None or data.empty:
            print("⚠️ 데이터가 없습니다. 기본값을 반환합니다.")
            return ("N/A", "N/A", "N/A", {}, go.Figure(), html.Div("데이터 없음"), "N/A")

        latest = data.iloc[-1]
        print(f"✅ 최신 데이터: {latest.name} ({latest.get('measurement', 'unknown')})")
        
        # 습도 그래프
        humidity_fig = create_line_humidity_figure(data)

        # MongoDB에서 로봇 작동 주기 가져오기
        cycle_count = 0
        try:
            if mongo_db is not None:
                latest_op = mongo_db.robot_operations.find_one(
                    {},
                    sort=[('operation_time', -1)]
                )
                if latest_op and 'load_cycle_count' in latest_op:
                    cycle_count = latest_op['load_cycle_count']
                    print(f"✅ MongoDB 로봇 주기: {cycle_count}")
                else:
                    print("⚠️ MongoDB에서 로봇 주기 데이터 없음")
        except Exception as e:
            print(f"❌ MongoDB 로봇 주기 조회 오류: {e}")
        
        cycle_txt = f"{cycle_count}회"
        
        # 토크 테이블 생성
        rows = []
        try:
            for i in range(6):
                key = f'joint_{i}'
                val = latest.get(key, random.uniform(0.5, 2.8))  # 없으면 랜덤값
                
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",  
                    value=val,
                    number={'suffix': " N·m", 'font': {'size': 17, 'color': 'white'}},
                    gauge={
                        'shape': "bullet",
                        'axis': {'range': [0, 3]},
                        'bar': {'color': "#1f77b4", 'thickness': 1.0},
                        'steps': [
                            {'range': [0, 2], 'color': "lightgray"},
                            {'range': [2, 2.5], 'color': "yellow"},
                            {'range': [2.5, 3], 'color': "red"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 2.5
                        }
                    }
                ))
                fig.update_layout(
                    height=60,
                    margin=dict(l=0, r=0, t=0, b=0), 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color='white')
                )
                rows.append(html.Tr([
                    html.Td(f"Joint {i}", style={
                        'color': 'white',
                        'fontSize': '14px',
                        'padding': '0px',
                        'margin': '0px',
                        'width': '60px',
                        'textAlign': 'right',
                        'verticalAlign': 'middle'
                    }),
                    html.Td(
                        dcc.Graph(figure=fig, config={'displayModeBar': False}),
                        style={'padding': '0px', 'margin': '0px', 'height': '60px', 'width': '300px'}
                    )
                ]))
        except Exception as e:
            print(f"❌ 토크 테이블 생성 오류: {e}")
            rows = [html.Tr([html.Td(f"토크 테이블 오류: {str(e)[:50]}", style={'color': 'red'})])]
        
        torque_table = html.Table(rows, style={'width': 'auto', 'borderSpacing': '4px'})

        # 반환값 생성
        result = (
            f"{latest.get('temperature_c', 'N/A')} °C",
            f"{latest.get('pressure_bar', 'N/A')} bar",
            f"{latest.get('speed_mm_per_s', 'N/A')} mm/s",
            {
                'position': 'absolute',
                'top': f"{latest.get('y', 20) * 10}px",
                'left': f"{latest.get('x', 20) * 10}px",
                'width': '10px',
                'height': '10px',
                'backgroundColor': 'red',
                'borderRadius': '50%',
                'boxShadow': '0 0 10px red'
            },
            humidity_fig,
            torque_table,
            cycle_txt
        )
        
        print(f"✅ 업데이트 #{n} 완료")
        return result

    except Exception as e:
        print(f"❌ update_sensor_display 전체 오류: {e}")
        print(f"❌ 오류 상세: {traceback.format_exc()}")
        
        # 오류 시 안전한 기본값 반환
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"오류 발생: {str(e)[:30]}...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            font=dict(size=14, color="red"),
            showarrow=False
        )
        error_fig.update_layout(**common_layout)
        
        return (
            "ERROR", "ERROR", "ERROR", 
            {'display': 'none'}, 
            error_fig, 
            html.Div(f"오류: {str(e)[:50]}", style={'color': 'red'}), 
            "ERROR"
        )

if __name__ == '__main__':
    print("=" * 80)
    print("🏭 스마트 팩토리 대시보드 with 실시간 스트리밍 배경 (v2)")
    print("=" * 80)
    print("📁 파일 구조:")
    print("  - integrated_dashboard_v2.py (메인 파일)")
    print("  - assets/streaming.html (스트리밍 배경)")
    print("  - assets/streaming.js (WebSocket 로직)")
    print("  - assets/logo.png, factory.png, robot.png (이미지 파일)")
    print("")
    print("📡 네트워크 정보:")
    print(f"  - 1번 PC: 172.18.73.60 (화면 송신)")
    print(f"  - 2번 PC: 172.18.73.63 (대시보드 + 스트리밍 수신)")
    print(f"  - 시그널링 서버: ws://172.18.73.63:3001")
    print(f"  - 대시보드 서버: http://localhost:8050")
    print("")
    print("🎨 특징:")
    print("  - 실시간 스트리밍이 배경으로 표시")
    print("  - 스마트 팩토리 대시보드가 오버레이로 표시")
    print("  - 반투명 배경으로 가독성 확보")
    print("  - 강화된 에러 처리 및 로깅")
    print("  - 데이터베이스 연결 실패 시 더미 데이터 사용")
    print("  - 실시간 스트리밍 로그 표시")
    print("")
    print("⌨️ 키보드 단축키:")
    print("  - F5: 스트리밍 재연결")
    print("  - F12: 스트리밍 배경 토글")
    print("  - 📋 로그 버튼: 스트리밍 로그 표시/숨김")
    print("=" * 80)
    print("🚀 통합 대시보드 시작...")
    print("📋 실행 순서:")
    print("  1. 2번 PC: node signaling_server.js")
    print("  2. 2번 PC: python integrated_dashboard_v2.py")
    print("  3. 1번 PC: python stable_screen_sender.py")
    print("  4. 브라우저: http://172.18.73.63:8050")
    print("=" * 80)
    
    # assets 폴더 확인
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    required_files = ['streaming.html', 'streaming.js']
    
    if not os.path.exists(assets_path):
        print("❌ assets 폴더가 없습니다. 생성해주세요.")
        sys.exit(1)
    
    for file_name in required_files:
        file_path = os.path.join(assets_path, file_name)
        if not os.path.exists(file_path):
            print(f"❌ assets/{file_name} 파일이 없습니다.")
            sys.exit(1)
    
    print("✅ assets 폴더 및 필수 파일 확인 완료")
    
    try:
        app.run_server(debug=False, host='172.18.73.63', port=8050)
    except Exception as e:
        print(f"❌ 172.18.73.63:8050 오류: {e}")
        try:
            app.run_server(debug=False, host='127.0.0.1', port=8051)
        except Exception as e2:
            print(f"❌ 127.0.0.1:8051 오류: {e2}")
            app.run_server(debug=False, host='localhost', port=8052)