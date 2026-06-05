import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from database.db import StatisticsRepository
from config import PINK, PURPLE, PINK_L, PURP_L

dash.register_page(__name__, path="/", name="Dashboard")

PLOT_CFG = {"displayModeBar": False}
PLOT_LAY = dict(paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=16,r=16,t=16,b=16),
                font=dict(family="Inter, Arial, sans-serif", size=12, color="#374151"),
                legend=dict(orientation="h", y=-0.15))

def _kpi_card(label, icon, color, kid):
    return html.Div([
        html.Div(className="kpi-stripe", style={"background": color}),
        html.Div([
            html.Div([
                html.Div(label, className="kpi-label"),
                html.Div("—", className="kpi-value", id=kid, style={"color": color}),
            ], style={"flex":"1"}),
            html.Div(icon, style={"fontSize":"28px","alignSelf":"center"}),
        ], className="kpi-body", style={"display":"flex","gap":"8px"}),
    ], className="kpi-card")


layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Dashboard", className="page-title"),
            html.P("Panoramica clinica", className="page-subtitle"),
        ]),
        dbc.Button("🔄  Aggiorna", id="dash-refresh", size="sm",
                   className="btn-outline-purple"),
    ], className="page-topbar"),

    html.Div([
        # KPI — testo pulito senza "previsti"
        dbc.Row([
            dbc.Col(_kpi_card("Pazienti totali",   "👥", PURPLE,    "kpi-patients"),       md=3),
            dbc.Col(_kpi_card("Classificazioni",   "🔬", PINK,      "kpi-classifications"),md=3),
            dbc.Col(_kpi_card("BCS",               "✂️", "#059669", "kpi-bcs"),            md=3),
            dbc.Col(_kpi_card("Mastectomia",       "🏥", "#DC2626", "kpi-mast"),           md=3),
        ], className="g-3 mb-3"),

        # Avg row: Età media | BMI medio | Distribuzione Gradi (%)
        dbc.Row([
            dbc.Col(html.Div([
                html.Div("—", className="avg-val", id="avg-age",   style={"color":PURPLE}),
                html.Div("Età media (anni)", className="avg-lbl"),
            ], className="avg-card"), md=4),

            dbc.Col(html.Div([
                html.Div("—", className="avg-val", id="avg-bmi",   style={"color":PINK}),
                html.Div("BMI medio", className="avg-lbl"),
            ], className="avg-card"), md=4),

            # Distribuzione gradi (piccolo pie inline)
            dbc.Col(html.Div([
                html.Div("Distribuzione Gradi", className="avg-lbl",
                         style={"marginBottom":"4px"}),
                dcc.Graph(id="mini-grade-pie", config=PLOT_CFG,
                          style={"height":"70px"},
                          figure=go.Figure().update_layout(
                              paper_bgcolor="white",margin=dict(l=0,r=0,t=0,b=0))),
            ], className="avg-card", style={"padding":"12px 16px"}), md=4),

        ], className="g-3 mb-3"),

        # Charts
        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Distribuzione predizioni", className="card-title"),
                dcc.Graph(id="pie-chart", config=PLOT_CFG, style={"height":"280px"}),
            ], className="card-box"), md=5),

            dbc.Col(html.Div([
                html.Div("BMI per tipo di predizione", className="card-title"),
                dcc.Graph(id="bmi-chart", config=PLOT_CFG, style={"height":"280px"}),
            ], className="card-box"), md=7),
        ], className="g-3"),

    ], style={"padding":"20px 24px"}),

    dcc.Interval(id="dash-interval", interval=60_000, n_intervals=0),
])


@callback(
    Output("kpi-patients","children"),  Output("kpi-classifications","children"),
    Output("kpi-bcs","children"),       Output("kpi-mast","children"),
    Output("avg-age","children"),       Output("avg-bmi","children"),
    Output("pie-chart","figure"),
    Output("bmi-chart","figure"),
    Output("mini-grade-pie","figure"),
    Input("dash-interval","n_intervals"),
    Input("dash-refresh","n_clicks"),
)
def update_dashboard(_i, _c):
    try:
        s     = StatisticsRepository.get_summary()
        grade = StatisticsRepository.get_grade_distribution()
    except Exception:
        s     = {"total_patients":0,"total_classifications":0,
                 "bcs_count":0,"mastectomy_count":0,
                 "avg_age":0,"avg_bmi":0,"avg_tumor_size":0}
        grade = {}

    # ── Pie predizioni ─────────────────────────────────────────────────────
    bcs  = s.get("bcs_count",0)
    mast = s.get("mastectomy_count",0)
    if bcs + mast > 0:
        pie = go.Figure(go.Pie(
            labels=["BCS","Mastectomy"], values=[bcs, mast],
            marker_colors=[PINK, PURPLE], hole=0.45,
            textinfo="percent+label",
            textfont=dict(size=11, family="Inter"),
        ))
    else:
        pie = go.Figure()
        pie.add_annotation(text="Nessun dato", x=0.5, y=0.5,
                           showarrow=False, font_color="#9CA3AF", font_size=13)
    pie.update_layout(**PLOT_LAY)

    # ── Box BMI per predizione ─────────────────────────────────────────────
    from database.db import PatientRepository
    import pandas as pd
    pts = PatientRepository.get_all()
    bmi_fig = go.Figure()
    if pts:
        df = pd.DataFrame(pts)
        for cls, color in [("BCS", PINK), ("Mastectomy", PURPLE)]:
            sub = df[df.get("last_prediction","") == cls]["bmi"].dropna()
            if len(sub):
                bmi_fig.add_trace(go.Box(
                    y=sub, name=cls,
                    marker_color=color, line_color=color,
                    fillcolor=color+"33", boxmean=True,
                ))
    bmi_fig.update_layout(**PLOT_LAY,
                          yaxis_title="BMI",
                          showlegend=True)
    if not pts:
        bmi_fig.add_annotation(text="Nessun dato", x=0.5, y=0.5,
                               showarrow=False, font_color="#9CA3AF", font_size=13)

    # ── Mini pie gradi ─────────────────────────────────────────────────────
    if grade:
        total = sum(grade.values()) or 1
        mini  = go.Figure(go.Pie(
            labels=[k.replace("Grade ","G") for k in grade.keys()],
            values=list(grade.values()),
            marker_colors=[PINK, PURPLE, "#0284C7"][:len(grade)],
            textinfo="percent", hole=0.3,
            textfont_size=10,
            showlegend=True,
        ))
        mini.update_layout(
            paper_bgcolor="white", margin=dict(l=0,r=0,t=0,b=0),
            legend=dict(orientation="h", font_size=10,
                        y=-0.3, x=0, xanchor="left"),
            height=110,
        )
    else:
        mini = go.Figure()
        mini.add_annotation(text="—", x=0.5, y=0.5,
                            showarrow=False, font_size=18, font_color="#9CA3AF")
        mini.update_layout(paper_bgcolor="white",
                           margin=dict(l=0,r=0,t=0,b=0), height=70)

    return (
        str(s.get("total_patients",0)),
        str(s.get("total_classifications",0)),
        str(s.get("bcs_count",0)),
        str(s.get("mastectomy_count",0)),
        str(s.get("avg_age",0)),
        str(s.get("avg_bmi",0)),
        pie, bmi_fig, mini,
    )
