import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from database.db import StatisticsRepository, ClassificationRepository, PatientRepository
from config import PINK, PURPLE, PINK_L, PURP_L

dash.register_page(__name__, path="/statistics", name="Statistiche")

PLOT_CFG = {"displayModeBar": False}
PLOT_LAY = dict(paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=20,r=20,t=30,b=20),
                font=dict(family="Inter,Arial,sans-serif",size=12,color="#374151"))

layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Statistiche & Analisi", className="page-title"),
            html.P("Analisi statistica del database", className="page-subtitle"),
        ]),
        dbc.Button("🔄  Aggiorna", id="stats-refresh",
                   className="btn-outline-purple"),
    ], className="page-topbar"),

    html.Div([
        dbc.Tabs([
            dbc.Tab(label="📊  Distribuzione", tab_id="dist",
                    label_style={"fontWeight":"600","fontSize":"13px"}),
            dbc.Tab(label="🔗  Correlazioni",  tab_id="corr",
                    label_style={"fontWeight":"600","fontSize":"13px"}),
            dbc.Tab(label="🔬  Predizioni",    tab_id="pred",
                    label_style={"fontWeight":"600","fontSize":"13px"}),
            dbc.Tab(label="🥗  Stile di vita", tab_id="life",
                    label_style={"fontWeight":"600","fontSize":"13px"}),
        ], id="stats-tabs", active_tab="dist",
           style={"marginBottom":"16px"}),

        html.Div(id="stats-content"),
        dcc.Interval(id="stats-interval", interval=999999),
    ], style={"padding":"20px 24px"}),
])


@callback(
    Output("stats-content","children"),
    Input("stats-tabs","active_tab"),
    Input("stats-refresh","n_clicks"),
    Input("stats-interval","n_intervals"),
)
def render_tab(tab, _clicks, _n):
    if tab == "dist": return _dist()
    if tab == "corr": return _corr()
    if tab == "pred": return _pred()
    if tab == "life": return _life()
    return html.Div()


def _dist():
    ages  = StatisticsRepository.get_age_distribution()
    bmis  = StatisticsRepository.get_bmi_distribution()
    grade = StatisticsRepository.get_grade_distribution()

    f_age  = go.Figure(go.Histogram(x=ages, nbinsx=12,
                        marker_color=PINK, marker_line_color="white",
                        marker_line_width=1))
    f_age.update_layout(**PLOT_LAY, title="Distribuzione Età")
    f_age.update_xaxes(title_text="Età (anni)")

    f_bmi = go.Figure(go.Histogram(x=bmis, nbinsx=12,
                        marker_color=PURPLE, marker_line_color="white",
                        marker_line_width=1))
    f_bmi.update_layout(**PLOT_LAY, title="Distribuzione BMI")
    f_bmi.update_xaxes(title_text="BMI")

    f_grade = go.Figure(go.Bar(
        x=list(grade.keys()), y=list(grade.values()),
        marker_color=[PINK, PURPLE, "#0284C7"][:len(grade)],
        marker_line_color="white", marker_line_width=1))
    f_grade.update_layout(**PLOT_LAY, title="Grading tumorale")

    cfg = {"displayModeBar":False}
    return dbc.Row([
        dbc.Col(html.Div([dcc.Graph(figure=f_age,  config=cfg, style={"height":"300px"})], className="card-box"), md=4),
        dbc.Col(html.Div([dcc.Graph(figure=f_bmi,  config=cfg, style={"height":"300px"})], className="card-box"), md=4),
        dbc.Col(html.Div([dcc.Graph(figure=f_grade,config=cfg, style={"height":"300px"})], className="card-box"), md=4),
    ], className="g-3")


def _corr():
    rows = PatientRepository.get_all()
    if len(rows) < 3:
        return html.P("Servono almeno 3 pazienti.", style={"color":"#6B7280","padding":"40px"})
    df   = pd.DataFrame(rows)
    nums = [c for c in ["age","bmi","tumor_size_mm","ki67_percent",
                         "eating_habit_score","physical_activity"] if c in df.columns]
    df_n = df[nums].dropna().astype(float)
    corr = df_n.corr()
    fig  = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns,
        colorscale="RdYlBu", zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}", textfont_size=11,
    ))
    fig.update_layout(**PLOT_LAY, title="Matrice di correlazione",
                      height=420)
    return html.Div([dcc.Graph(figure=fig, config={"displayModeBar":False})],
                    className="card-box")


def _pred():
    results = ClassificationRepository.get_all()
    if not results:
        return html.P("Nessuna classificazione.", style={"color":"#6B7280","padding":"40px"})
    bcs  = sum(1 for r in results if r["predicted_class"]=="BCS")
    mast = sum(1 for r in results if r["predicted_class"]=="Mastectomy")
    confs= [r["confidence_bcs"] for r in results if r.get("confidence_bcs") is not None]

    pie = go.Figure(go.Pie(
        labels=["BCS","Mastectomy"], values=[bcs,mast],
        marker_colors=[PINK, PURPLE], hole=0.4,
        textfont=dict(size=12)))
    pie.update_layout(**PLOT_LAY, title="Proporzione predizioni", height=300)

    hist = go.Figure(go.Histogram(x=confs, nbinsx=10,
                                  marker_color=PINK, marker_line_color="white"))
    hist.update_layout(**PLOT_LAY, title="Distribuzione confidenza BCS (%)", height=300)
    hist.update_xaxes(title_text="Confidenza (%)")

    cfg = {"displayModeBar":False}
    return dbc.Row([
        dbc.Col(html.Div([dcc.Graph(figure=pie,  config=cfg)], className="card-box"), md=5),
        dbc.Col(html.Div([dcc.Graph(figure=hist, config=cfg)], className="card-box"), md=7),
    ], className="g-3")


def _life():
    data = StatisticsRepository.get_eating_vs_prediction()
    if not data:
        return html.P("Nessun dato.", style={"color":"#6B7280","padding":"40px"})
    df  = pd.DataFrame(data)
    fig = go.Figure()
    for cls, col in [("BCS",PINK),("Mastectomy",PURPLE)]:
        sub = df[df["class"]==cls]["score"]
        if len(sub):
            fig.add_trace(go.Violin(
                y=sub, name=cls, box_visible=True,
                meanline_visible=True, fillcolor=col,
                opacity=0.7, line_color="white",
                marker_color=col))
    fig.update_layout(**PLOT_LAY, title="Score alimentare per predizione",
                      yaxis_title="Score (0–10)", height=380, violinmode="group")
    return html.Div([dcc.Graph(figure=fig, config={"displayModeBar":False})],
                    className="card-box")
