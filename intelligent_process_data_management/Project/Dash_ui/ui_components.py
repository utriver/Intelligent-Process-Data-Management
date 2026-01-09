from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State

class ClickToModal:
    def __init__(self, app, graph_id, figure_generator, style, layout_config):
        self.app = app
        self.graph_id = graph_id
        self.figure_generator = figure_generator
        self.style = style
        self.layout_config = layout_config
        self.setup_callbacks()
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output(f"{self.graph_id}", "figure"),  # 기본 그래프
             Output(f"{self.graph_id}-modal-graph", "figure"),  # 모달 그래프
             Output(f"{self.graph_id}-modal", "style")],
            [Input('update-interval', 'n_intervals'),
             Input(f"{self.graph_id}-container", "n_clicks"),
             Input(f"{self.graph_id}-close", "n_clicks")],
            [State(f"{self.graph_id}-modal", "style")],
            prevent_initial_call=True
        )
        def update_modal(n_intervals, open_clicks, close_clicks, current_style):
            ctx = callback_context
            figure = self.figure_generator()
            
            if not ctx.triggered:
                return figure, figure, {"display": "none"}
                
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            # 현재 모달 상태 확인
            is_modal_open = current_style and current_style.get("display") == "block"
            
            if trigger_id == f"{self.graph_id}-close":
                modal_style = {"display": "none"}
            elif trigger_id == f"{self.graph_id}-container" and not is_modal_open:
                modal_style = {
                    "display": "block",
                    "position": "fixed",
                    "top": "50%",
                    "left": "50%",
                    "transform": "translate(-50%, -50%)",
                    "backgroundColor": "rgba(0,0,0,0.8)",
                    "padding": "20px",
                    "borderRadius": "10px",
                    "zIndex": "1000",
                    "width": "80%",
                    "height": "80%"
                }
            else:
                modal_style = current_style or {"display": "none"}

            return figure, figure, modal_style

    def components(self):
        return [
            html.Div([
                dcc.Graph(
                    id=self.graph_id,
                    style=self.style,
                    config={'displayModeBar': False},
                    figure=self.figure_generator()  # 초기 figure 설정
                )
            ], id=f"{self.graph_id}-container", style={"cursor": "pointer"}),
            
            html.Div([
                html.Button(
                    "×",
                    id=f"{self.graph_id}-close",
                    style={
                        "position": "absolute",
                        "right": "0",  # 오른쪽 여백 제거
                        "top": "0",    # 위쪽 여백 제거
                        "color": "red",
                        "fontSize": "72px",  # 글자 크기 더 크게
                        "cursor": "pointer",
                        "fontWeight": "bold",
                        "width": "120px",   # 클릭 영역 확대
                        "height": "120px",  # 클릭 영역 확대
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "background": "none",  # 배경 제거
                        "border": "none",     # 테두리 제거
                        "zIndex": "1001"      # 항상 최상단에 표시
                    }
                ),  
                dcc.Graph(
                    id=f"{self.graph_id}-modal-graph",
                    style={"width": "100%", "height": "100%"},
                    config={'displayModeBar': False},
                    figure=self.figure_generator()  # 초기 figure 설정
                )
            ], id=f"{self.graph_id}-modal", style={"display": "none"})
        ]