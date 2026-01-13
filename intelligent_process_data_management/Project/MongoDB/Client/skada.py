import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from pymongo import MongoClient

client = MongoClient('mongodb://172.19.97.169:27017/')
db = client['test_0416']
collection = db['data_collection1']

docs = list(collection.find({"type": {"$exists": False}}, {"_id": 0}))
df = pd.DataFrame(docs)

# 결과 출력
print(df)

# 염료별 색상 매핑
color_map = {
    '청색': '#1f77b4',
    '적색': '#d62728',
    '노랑': '#ffbf00',
    '흑색': '#2f2f2f'
}

# bar_dye 그래프 (go 방식, 색상 지정)
bar_dye = go.Figure()
for idx, row in df_dye.iterrows():
    bar_dye.add_trace(go.Bar(
        x=[row['염료 종류']],
        y=[row['재고량']],
        name=row['염료 종류'],
        marker_color=color_map[row['염료 종류']]
    ))
bar_dye.update_layout(
    title='플라스틱 염료 재고 현황',
    title_font_size=24,
    font=dict(size=16),
    xaxis_title='염료 종류',
    xaxis_title_font_size=18,
    yaxis_title='재고량',
    yaxis_title_font_size=18,
    showlegend=False,
    template='plotly_dark',
    plot_bgcolor='#111',
    paper_bgcolor='#111'
)

# 생산수량 막대 그래프
bar_production = px.bar(df_production, x='날짜', y='생산수량', title='일일 생산수량')
bar_production.update_layout(
    title_font_size=24,
    font=dict(size=16),
    xaxis_title_font_size=18,
    yaxis_title_font_size=18,
    template='plotly_dark',
    plot_bgcolor='#111',
    paper_bgcolor='#111'
)

# 불량률 파이 그래프
pie_defect = px.pie(
    values=df_production['불량률'] * df_production['생산수량'],
    names=df_production['날짜'].dt.strftime('%m-%d'),
    title='불량 수량 비율'
)
pie_defect.update_layout(
    title_font_size=24,
    font=dict(size=16),
    legend_font_size=14,
    template='plotly_dark',
    plot_bgcolor='#111',
    paper_bgcolor='#111'
)

# 사이클 수 선 그래프
line_cycles = px.line(df_production, x='날짜', y='사이클수', title='사이클 수 변화')
line_cycles.update_layout(
    title_font_size=24,
    font=dict(size=16),
    xaxis_title_font_size=18,
    yaxis_title_font_size=18,
    template='plotly_dark',
    plot_bgcolor='#111',
    paper_bgcolor='#111'
)

# Dash 앱 구성
app = dash.Dash(__name__)
app.layout = html.Div(style={
    'backgroundColor': '#000',  # ✅ 전체 배경 어둡게 맞춤
    'minHeight': '100vh',
    'padding': '30px'
}, children=[

    # 🔥 상단: 로고 (왼쪽) + 제목 (오른쪽)
    html.Div([
        html.Img(src='/assets/logo.png', style={
            'height': '160px',           # ✅ 로고 키움
            'marginRight': '40px'
        }),
        html.H1("플라스틱 사출 공정 모니터링", style={
            'color': '#fff',
            'margin': 'auto 0',
            'fontSize': '44px',           # ✅ 제목 키움
            'fontWeight': 'bold'
        })
    ], style={
        'display': 'flex',
        'flexDirection': 'row',
        'alignItems': 'center',
        'justifyContent': 'flex-start',
        'marginBottom': '50px'
    }),

    # 📊 첫 줄 그래프
    html.Div([
        dcc.Graph(figure=bar_production, style={'width': '48%', 'display': 'inline-block', 'margin': '0 1%'}),
        dcc.Graph(figure=pie_defect, style={'width': '48%', 'display': 'inline-block', 'margin': '0 1%'})
    ], style={'textAlign': 'center', 'marginBottom': '40px'}),

    # 📈 두 번째 줄 그래프
    html.Div([
        dcc.Graph(figure=line_cycles, style={'width': '48%', 'display': 'inline-block', 'margin': '0 1%'}),
        dcc.Graph(figure=bar_dye, style={'width': '48%', 'display': 'inline-block', 'margin': '0 1%'})
    ], style={'textAlign': 'center'})
])


# 실행
if __name__ == '__main__':
    app.run(debug=True, port=8050)
