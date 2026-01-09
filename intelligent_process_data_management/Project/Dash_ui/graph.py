import dash
from dash import dcc, html, Input, Output
import os
import h5py
import numpy as np
import plotly.graph_objs as go
import pandas as pd
import base64
from dash.dependencies import State
from dash import ctx
import sys
import logging

app = dash.Dash(__name__)
app.title = '📈 HDF5 Visualization Dashboard'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HDF5_DIR = "hdf5_logs"

GRAPH_TITLES = [
    "🤖 로봇 관절 토크",
    "📍 로봇 위치",
    "📊 생산품 현황",
    "⬇️ 보압",
    "🌡️ 온도",
    "🔩 사출 속도",
    "💧 습도"
]

# 필수 데이터셋 정의
REQUIRED_DATASETS = {
    'robot_arm_torque': ['timestamp'] + [f'joint_{i}' for i in range(6)],
    'logistics_robot_position_rotation': ['timestamp', 'x', 'y'],
    'finished_product_count': ['timestamp', 'normal_count', 'defect_count'],
    'pressure_Mpa': ['timestamp', 'pressure_mpa'],
    'temperature_c': ['timestamp', 'temperature_c'],
    'linear_velocity_mm_s': ['timestamp', 'linear_velocity_mm_s'],
    'humidity_percent': ['timestamp', 'humidity_percent']
}

# 데이터 그룹 정의
groups = [
    ('finished_product_count', [
        ('normal_count', '#2ecc71', '정상품'),
        ('defect_count', '#e74c3c', '불량품')
    ]),
    ('pressure_Mpa', 'pressure_mpa'),
    ('temperature_c', 'temperature_c'),
    ('linear_velocity_mm_s', 'linear_velocity_mm_s'),
    ('humidity_percent', 'humidity_percent')
]

# 파일 목록 및 최대 파일 크기
hdf5_files = [f for f in os.listdir(HDF5_DIR) if f.endswith(".h5")]
MAX_FILE_SIZE = 100 * 1024 * 1024

# 그래프 공통 레이아웃
def get_common_layout(title):
    return {
        'height': 500,
        'title': title,
        'xaxis': {
            'type': 'date',
            'rangeslider': {'visible': True},
        },
        'dragmode': 'zoom',  # 드래그로 영역 확대 가능
        'showlegend': True,
        'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50},
        'modebar': {
            'add': [
                'drawopenpath',
                'eraseshape',
                'zoomin',
                'zoomout',
                'autoscale',
                'reset'
            ]
        },
        'hovermode': 'closest'  # 포인트에 마우스 오버시 데이터 표시
    }

app.layout = html.Div([
    html.H3("HDF5 공정 데이터", style={"textAlign": "center"}),

    html.Div([
        html.Label("📁 HDF5 파일 선택:"),
        dcc.Dropdown(
            id='hdf5-selector',
            options=[{'label': f, 'value': f} for f in hdf5_files],
            value=hdf5_files[0] if hdf5_files else None,
            style={"width": "60%"}
        )
    ], style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        html.Label("📂 HDF5 파일 업로드:"),
        dcc.Upload(
            id='upload-hdf5',
            children=html.Button('🔍 파일 선택 및 업로드'),
            multiple=False
        )
    ], style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        html.Div([
            dcc.Graph(id=f'graph-{i}', config={'displayModeBar': True, 'scrollZoom': True})
        ], style={"width": "32%", "display": "inline-block", "margin": "0.5%"})
        for i in range(7)
    ])
])

@app.callback(
    [Output(f'graph-{i}', 'figure') for i in range(7)],
    Input('hdf5-selector', 'value')
)
def update_graphs(filename):
    def decode_timestamps(ts_array):
        return pd.to_datetime([ts.decode('utf-8') if isinstance(ts, bytes) else str(ts) for ts in ts_array])
    
    empty_fig = go.Figure(layout=go.Layout(title="❌ No Data"))
    if not filename:
        return [empty_fig] * 7

    path = os.path.join(HDF5_DIR, filename)
    try:
        with h5py.File(path, 'r') as f:
            # 데이터셋 존재 여부 확인
            missing_groups = []
            for group, fields in REQUIRED_DATASETS.items():
                if group not in f:
                    missing_groups.append(group)
                elif any(field not in f[group] for field in fields):
                    missing_fields = [field for field in fields if field not in f[group]]
                    missing_groups.append(f"{group} (필드: {', '.join(missing_fields)})")
            
            if missing_groups:
                error_msg = f"다음 데이터가 없습니다:\n{', '.join(missing_groups)}"
                logger.error(error_msg)
                return [go.Figure(layout=go.Layout(title=f"❌ 오류: {error_msg}"))] * 7

            figures = []

            # 1. 로봇팔 힘/토크
            fig0 = go.Figure()
            ts = decode_timestamps(f['/robot_arm_torque/timestamp'][()])
            for j in range(6):
                fig0.add_trace(go.Scatter(
                    x=ts,
                    y=f[f'/robot_arm_torque/joint_{j}'][()],
                    mode='markers',
                    name=f'Joint {j}',
                    marker=dict(size=1)
                ))
            fig0.update_layout(**get_common_layout(GRAPH_TITLES[0]))
            figures.append(fig0)

            # 2. 물류로봇 위치/회전
            fig1 = go.Figure()
            ts = decode_timestamps(f['/logistics_robot_position_rotation/timestamp'][()])
            for axis in ['x', 'y']:
                fig1.add_trace(go.Scatter(
                    x=ts,
                    y=f[f'/logistics_robot_position_rotation/{axis}'][()],
                    mode='markers',
                    name=axis,
                    marker=dict(size=1)
                ))
            fig1.update_layout(**get_common_layout(GRAPH_TITLES[1]))
            figures.append(fig1)

            # 3~7: 데이터 그룹
            for i, group_info in enumerate(groups):
                fig = go.Figure()
                ts = decode_timestamps(f[f'/{group_info[0]}/timestamp'][()])
                
                if isinstance(group_info[1], list):  # 생산품 현황
                    for field, color, name in group_info[1]:
                        fig.add_trace(go.Scatter(
                            x=ts,
                            y=f[f'/{group_info[0]}/{field}'][()],
                            mode='markers',
                            name=name,
                            marker=dict(color=color, size=6)
                        ))
                    layout = get_common_layout(GRAPH_TITLES[i+2])
                    layout['legend'] = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    fig.update_layout(**layout)
                else:  # 단일값 그래프
                    fig.add_trace(go.Scatter(
                        x=ts,
                        y=f[f'/{group_info[0]}/{group_info[1]}'][()],
                        mode='markers',
                        name=group_info[0],
                        marker=dict(size=6)
                    ))
                    fig.update_layout(**get_common_layout(GRAPH_TITLES[i+2]))
                
                figures.append(fig)
            
            return figures[:7]

    except Exception as e:
        logger.error(f"그래프 업데이트 중 오류 발생: {str(e)}")
        return [go.Figure(layout=go.Layout(title=f"❌ 오류: {str(e)}"))] * 7

@app.callback(
    Output('hdf5-selector', 'options'),
    Output('hdf5-selector', 'value'),
    Input('upload-hdf5', 'contents'),
    State('upload-hdf5', 'filename'),
    prevent_initial_call=True
)
def save_uploaded_file(contents, filename):
    if not contents or not filename:
        logger.warning("파일이 선택되지 않았습니다.")
        raise dash.exceptions.PreventUpdate
    
    try:
        if not filename.endswith(".h5"):
            logger.error(f"잘못된 파일 형식입니다: {filename}")
            raise ValueError("HDF5 파일(.h5)만 업로드 가능합니다.")

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        file_size = sys.getsizeof(decoded)
        
        logger.info(f"업로드된 파일: {filename}, 크기: {file_size / (1024*1024):.2f}MB")
        
        if file_size > MAX_FILE_SIZE:
            logger.error(f"파일이 너무 큽니다: {file_size / (1024*1024):.2f}MB")
            raise ValueError(f"파일 크기는 100MB를 초과할 수 없습니다. (현재: {file_size / (1024*1024):.2f}MB)")

        if not os.path.exists(HDF5_DIR):
            logger.info(f"디렉토리 생성: {HDF5_DIR}")
            os.makedirs(HDF5_DIR)

        path = os.path.join(HDF5_DIR, filename)
        with open(path, 'wb') as f:
            f.write(decoded)
        logger.info(f"파일 저장 완료: {path}")

        files = [f for f in os.listdir(HDF5_DIR) if f.endswith(".h5")]
        logger.info(f"현재 파일 목록: {files}")
        
        return [{'label': f, 'value': f} for f in files], filename

    except Exception as e:
        logger.error(f"업로드 중 오류 발생: {str(e)}")
        raise dash.exceptions.PreventUpdate

if __name__ == '__main__':
    if not os.path.exists(HDF5_DIR):
        os.makedirs(HDF5_DIR)
        logger.info(f"디렉토리 생성됨: {HDF5_DIR}")
        
    app.run(debug=True, port=8051)