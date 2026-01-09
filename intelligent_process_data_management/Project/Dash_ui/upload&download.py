import dash
from dash import dcc, html, Input, Output, State, ctx
import os
import base64
import socket
from dash import ALL
from datetime import datetime
import numpy as np

app = dash.Dash(__name__)
app.title = "📁 파일 업로드/다운로드"

UPLOAD_DIR = "uploded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_file_type(fname):
    return os.path.splitext(fname)[-1].replace('.', '').upper() or "UNKNOWN"

def get_modified_time(fname):
    ts = os.path.getmtime(os.path.join(UPLOAD_DIR, fname))
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def build_file_list():
    files = [f for f in os.listdir(UPLOAD_DIR)]
    if not files:
        return html.P("📂 현재 업로드된 파일이 없습니다.")

    return html.Ul([
        html.Li([
            html.Span(f"📄 {fname} ({get_file_type(fname)} | {get_modified_time(fname)}) ", style={"marginRight": "10px"}),
            html.Button("📅 다운로드", id={'type': 'download-button', 'index': fname}, n_clicks=0),
            html.Button("🗑️ 삭제", id={'type': 'delete-button', 'index': fname}, n_clicks=0, style={"marginLeft": "10px"})
        ])
        for fname in sorted(files)
    ], style={"listStyle": "none", "padding": 0})

app.layout = html.Div([
    html.H2("📄 파일 업로드 / 다운로드 / 삭제", style={"textAlign": "center", "marginTop": "20px"}),

    html.Hr(),

    html.Div([
        html.Label("📂 파일 업로드", style={"fontWeight": "bold", "fontSize": "18px"}),
        dcc.Upload(
            id='upload-file',
            children=html.Button('🔍 파일 선택 및 업로드', style={
                "padding": "10px 20px",
                "fontSize": "16px",
                "cursor": "pointer",
                "backgroundColor": "#007bff",
                "color": "white",
                "border": "none",
                "borderRadius": "5px"
            }),
            multiple=False
        ),
    ], style={"textAlign": "center", "marginBottom": "40px"}),

    html.Hr(),

    html.Div([
        html.Label("📁 파일 목록", style={"fontWeight": "bold", "fontSize": "18px"}),
        html.Div(id='file-list-area', style={"marginTop": "20px"}),
        dcc.Download(id="download-file")
    ], style={"textAlign": "center", "marginBottom": "40px"}),

    html.Hr()
])

# 🔁 업로드/삭제 후 목록 갱신
@app.callback(
    Output('file-list-area', 'children'),
    Input('upload-file', 'contents'),
    State('upload-file', 'filename'),
    Input({'type': 'delete-button', 'index': ALL}, 'n_clicks'),
    State({'type': 'delete-button', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def refresh_list(upload_contents, upload_filename, delete_clicks, delete_ids):
    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and triggered['type'] == 'delete-button':
        fname = triggered['index']
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    elif upload_contents and upload_filename:
        save_path = os.path.join(UPLOAD_DIR, upload_filename)
        content_type, content_string = upload_contents.split(',')
        decoded = base64.b64decode(content_string)
        with open(save_path, 'wb') as f:
            f.write(decoded)

    return build_file_list()

@app.callback(
    Output("download-file", "data"),
    Input({'type': 'download-button', 'index': ALL}, 'n_clicks_timestamp'),
    State({'type': 'download-button', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def handle_download(timestamps, btn_ids):
    print("📥 [DEBUG] Download Callback Triggered")
    print("🧩 ctx.triggered_id:", ctx.triggered_id)
    print("🕒 timestamps:", timestamps)

    if not timestamps or all(ts is None for ts in timestamps):
        raise dash.exceptions.PreventUpdate

    max_index = int(np.argmax([ts if ts else -1 for ts in timestamps]))
    fname = btn_ids[max_index]['index']
    print(f"✅ [INFO] 다운로드 시작: {fname}")
    return dcc.send_file(os.path.join(UPLOAD_DIR, fname))

if __name__ == '__main__':
    ip = get_local_ip()
    print("\n" + "="*50)
    print("🚀 Dash 웹 서버 실행 완료!")
    print(f"🔗 접속 주소: http://{ip}:8052")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=8052)
