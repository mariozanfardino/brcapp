import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from config import PINK, PURPLE

dash.register_page(__name__, path="/patient/report", name="Report Paziente")

PLOT_CFG = {"displayModeBar": False}
PLOT_LAY = dict(paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=16,r=16,t=24,b=16),
                font=dict(family="Inter,Arial,sans-serif", size=12))


def layout():
    return html.Div([
        dcc.Location(id="report-url"),
        html.Div(id="report-body"),
        dcc.Interval(id="report-init", interval=300, n_intervals=0, max_intervals=1),
    ])


@callback(
    Output("report-body","children"),
    Input("report-init","n_intervals"),
    State("patient-store","data"),
)
def render_report(_, patient):
    if not patient:
        return dcc.Location(href="/patient/login", id="redir-pt")
    return _build_report(patient)


def _build_report(p):
    initials = (p.get("initials") or p.get("code","?"))[0].upper()
    pred      = p.get("last_prediction")
    pred_color= {"BCS":"#059669","Mastectomy":"#DC2626"}.get(pred,"#6B7280")
    pred_bg   = {"BCS":"#D1FAE5","Mastectomy":"#FEE2E2"}.get(pred,"#F4F6F9")
    pred_icon = {"BCS":"✂️","Mastectomy":"🏥"}.get(pred,"—")

    return html.Div([
        # Topbar
        html.Div([
            html.Div([
                html.H1("La mia Area Personale", className="page-title"),
                html.P("Report clinico personale — riservato e confidenziale",
                       className="page-subtitle"),
            ]),
            html.A([
                dbc.Button("↩  Esci", color="light",
                           style={"borderRadius":"8px","fontSize":"13px"})
            ], href="/patient/login"),
        ], className="page-topbar"),

        html.Div([

            # ── Hero paziente ─────────────────────────────────────────────────
            html.Div([
                html.Div(initials, className="patient-avatar"),
                html.Div([
                    html.Div(f"Paziente {p.get('code','')}", className="patient-hero-name"),
                    html.Div(
                        f"Età: {p.get('age','—')} anni  ·  BMI: {p.get('bmi','—')}  ·  "
                        f"Ultimo aggiornamento: {p.get('last_clf_date','—')}",
                        className="patient-hero-sub"),
                ]),
            ], className="patient-hero"),

            dbc.Row([
                # ── Colonna sinistra ──────────────────────────────────────────
                dbc.Col([

                    # Predizione corrente
                    html.Div("🔬  Risultato più recente", className="report-section-title"),
                    html.Div([
                        html.Div(pred_icon, className="prediction-hero-icon"),
                        html.Div(pred or "Nessuna classificazione",
                                 className="prediction-hero-label",
                                 style={"color": pred_color}),
                        html.Div(f"Data: {p.get('last_clf_date','—')}",
                                 className="prediction-hero-date"),
                        # Confidence bars
                        html.Div([
                            _conf_bar("BCS",        p.get("last_conf_bcs"),  "#059669"),
                            _conf_bar("Mastectomy", p.get("last_conf_mast"), "#DC2626"),
                        ], style={"marginTop":"16px","textAlign":"left"}) if pred else html.Div(),
                    ], className="prediction-hero",
                       style={"borderColor": pred_color, "background": pred_bg,
                              "marginBottom":"16px"}),

                    # Dati clinici
                    html.Div("🩺  Dati Clinici", className="report-section-title"),
                    html.Div([
                        _clin_item("Diametro tumore", f"{p.get('tumor_size_mm','—')} mm"),
                        _clin_item("Grado tumorale",  f"G{p.get('grade','—')}"),
                        _clin_item("Ki67",            f"{p.get('ki67_percent','—')}%"),
                        _clin_item("ER",  "Positivo" if p.get("er_status")   else "Negativo",
                                   "#059669" if p.get("er_status") else "#DC2626"),
                        _clin_item("PR",  "Positivo" if p.get("pr_status")   else "Negativo",
                                   "#059669" if p.get("pr_status") else "#DC2626"),
                        _clin_item("HER2","Positivo" if p.get("her2_status") else "Negativo",
                                   "#059669" if p.get("her2_status") else "#DC2626"),
                    ], className="clinical-grid"),

                    # Stile di vita
                    html.Div("🥗  Stile di Vita", className="report-section-title"),
                    html.Div([
                        _lifestyle_bar("Score alimentare",  p.get("eating_habit_score"), PINK),
                        _lifestyle_bar("Attività fisica",   p.get("physical_activity"),  PURPLE),
                    ], className="card-box"),

                ], md=5),

                # ── Colonna destra: grafici ───────────────────────────────────
                dbc.Col([

                    # Grafico placeholder — da definire
                    html.Div("📈  Analisi", className="report-section-title"),
                    html.Div([
                        html.Div([
                            html.Div("📊", style={"fontSize":"36px","marginBottom":"8px"}),
                            html.Div("Grafico in fase di definizione",
                                     style={"fontSize":"14px","fontWeight":"600",
                                            "color":"#374151","marginBottom":"4px"}),
                            html.Div("Questa sezione verrà aggiornata con un grafico personalizzato.",
                                     style={"fontSize":"12px","color":"#9CA3AF"}),
                        ], style={"textAlign":"center","padding":"32px 20px"}),
                    ], className="card-box mb-3",
                       style={"border":"2px dashed #E5E7EB","background":"#FAFAFA"}),

                    # Radar indicatori clinici
                    html.Div("🎯  Profilo clinico", className="report-section-title"),
                    html.Div([
                        dcc.Graph(
                            figure=_radar_chart(p),
                            config=PLOT_CFG,
                            style={"height":"300px"},
                        ),
                    ], className="card-box mb-3"),

                    # Nota legale
                    html.Div([
                        html.Span("ℹ️ ", style={"fontSize":"14px"}),
                        html.Span(
                            "Questo report è generato automaticamente da un modello AI "
                            "a supporto del clinico. Non sostituisce la valutazione medica. "
                            "Per qualsiasi dubbio contatta il tuo medico.",
                            style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.6"},
                        ),
                    ], style={"background":"#FEF9C3","borderRadius":"10px",
                               "padding":"14px 16px","border":"1px solid #FDE68A"}),

                ], md=7),
            ], className="g-3"),

        ], style={"padding":"20px 24px"}),
    ])


# ── Helper components ─────────────────────────────────────────────────────────
def _clin_item(label, value, color="#1A1A2E"):
    return html.Div([
        html.Div(label, className="clinical-item-label"),
        html.Div(value, className="clinical-item-value", style={"color":color}),
    ], className="clinical-item")


def _conf_bar(label, value, color):
    pct = round(value, 1) if value is not None else 0
    return html.Div([
        html.Div(style={"display":"flex","justifyContent":"space-between","marginBottom":"3px"},
                 children=[
                     html.Span(label, className="lifestyle-bar-label"),
                     html.Span(f"{pct}%", style={"fontSize":"12px","fontWeight":"700","color":color}),
                 ]),
        html.Div(html.Div(style={
            "width":f"{pct}%","background":color,
        }, className="lifestyle-bar-fill"), className="lifestyle-bar-wrap"),
    ], style={"marginBottom":"10px"})


def _lifestyle_bar(label, value, color):
    pct = round((value or 0) / 10 * 100, 0)
    score = value or 0
    return html.Div([
        html.Div(style={"display":"flex","justifyContent":"space-between","marginBottom":"4px"},
                 children=[
                     html.Span(label, className="lifestyle-bar-label"),
                     html.Span(f"{score}/10",
                               style={"fontSize":"13px","fontWeight":"700","color":color}),
                 ]),
        html.Div(html.Div(style={
            "width":f"{pct}%","background":color,
        }, className="lifestyle-bar-fill"), className="lifestyle-bar-wrap"),
    ], style={"marginBottom":"14px"})


def _history_chart(history):
    fig = go.Figure()
    if not history:
        fig.add_annotation(text="Nessuna classificazione", x=0.5, y=0.5,
                           showarrow=False, font_size=13, font_color="#6B7280")
        fig.update_layout(**PLOT_LAY)
        return fig

    dates   = [h["date"] for h in history][::-1]
    bcs_v   = [h.get("conf_bcs")  or 0 for h in history][::-1]
    mast_v  = [h.get("conf_mast") or 0 for h in history][::-1]

    fig.add_trace(go.Scatter(x=dates, y=bcs_v,  name="BCS %",
                             line=dict(color=PINK,   width=2.5),
                             mode="lines+markers", marker_size=7))
    fig.add_trace(go.Scatter(x=dates, y=mast_v, name="Mastectomy %",
                             line=dict(color=PURPLE, width=2.5),
                             mode="lines+markers", marker_size=7))
    fig.update_layout(**PLOT_LAY,
                      yaxis=dict(range=[0,100], title="Confidenza (%)"),
                      legend=dict(orientation="h",y=-0.25))
    return fig


def _radar_chart(p):
    # Normalizza valori su scala 0-10 per il radar
    def safe(v, mn, mx):
        if v is None: return 0
        return round((float(v)-mn)/(mx-mn)*10, 1)

    categories = ["Alimentazione","Attività fisica","BMI sano",
                  "Ki67 basso","Età giovane","Dim. piccola"]
    values = [
        p.get("eating_habit_score") or 0,
        p.get("physical_activity")  or 0,
        safe(p.get("bmi"), 30, 18),          # BMI sano = vicino a 22
        safe(p.get("ki67_percent"), 80, 0),  # Ki67 basso = meglio
        safe(p.get("age"), 80, 30),          # Età giovane = meglio
        safe(p.get("tumor_size_mm"), 60, 0), # Tumore piccolo = meglio
    ]
    values = [max(0, min(10, v)) for v in values]
    values_closed = values + [values[0]]
    cats_closed   = categories + [categories[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values_closed, theta=cats_closed,
        fill="toself", fillcolor="rgba(214,51,132,0.15)",
        line=dict(color=PINK, width=2),
        name="Profilo",
    ))
    fig.update_layout(
        **PLOT_LAY,
        polar=dict(
            bgcolor="white",
            radialaxis=dict(visible=True, range=[0,10],
                            tickfont_size=9, gridcolor="#E5E7EB"),
            angularaxis=dict(tickfont_size=11, gridcolor="#E5E7EB"),
        ),
        showlegend=False,
    )
    return fig
