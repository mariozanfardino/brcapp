import dash
from dash import html, dcc, dash_table, callback, Output, Input, State, ALL, ctx
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from config import PINK, PURPLE

dash.register_page(__name__, path="/patients", name="Pazienti")

# Colonne principali mostrate in tabella
MAIN_COLS = [
    {"name":"Codice",        "id":"code"},
    {"name":"Peso (kg)",     "id":"peso"},
    {"name":"Altezza (cm)",  "id":"altezza"},
    {"name":"Menopausa",     "id":"menopausa_d"},
    {"name":"Fumo",          "id":"fumo_d"},
    {"name":"BI-RADS",       "id":"biRadioClinico"},
    {"name":"Citologia",     "id":"citologia"},
    {"name":"Focalità",      "id":"focalita"},
    {"name":"Linfon. DX",    "id":"stato_linfonodaleXX"},
    {"name":"Linfon. SX",    "id":"stato_linfondaleXX"},
    {"name":"Pred. AI",      "id":"last_prediction"},
    {"name":"DISEASE",       "id":"DISEASE"},
    {"name":"Aggiunto",      "id":"created_at"},
]

layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Archivio Pazienti", className="page-title"),
            html.P(f"Tabella principale · {len(MAIN_COLS)-1} colonne mostrate",
                   className="page-subtitle"),
        ]),
        html.Div([
            dbc.Input(id="pt-search", placeholder="  Cerca codice…",
                      debounce=True,
                      style={"width":"220px","height":"38px",
                             "borderRadius":"8px","fontSize":"13px"}),
            dbc.Button("＋  Nuovo", id="btn-new-patient", className="btn-pink"),
            dbc.Button("🔑  PIN", href="/admin/pins",
                       className="btn-outline-purple",
                       external_link=False),
        ], style={"display":"flex","gap":"10px","alignItems":"center"}),
    ], className="page-topbar"),

    html.Div([
        dash_table.DataTable(
            id="patients-table",
            columns=MAIN_COLS,
            data=[],
            row_selectable="single",
            selected_rows=[],
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            page_size=20,
            style_table={"borderRadius":"12px","overflow":"hidden","border":"1px solid #E5E7EB"},
            style_cell={"textAlign":"left","padding":"10px 13px","fontSize":"13px",
                        "fontFamily":"Inter,Arial,sans-serif","border":"none",
                        "borderBottom":"1px solid #F3F4F6"},
            style_header={"backgroundColor":"#EDE7F6","color":"#4A235A","fontWeight":"700",
                          "fontSize":"11px","textTransform":"uppercase","letterSpacing":"0.5px",
                          "border":"none","borderBottom":"1px solid #E5E7EB"},
            style_data_conditional=[
                {"if":{"filter_query":"{last_prediction} = 'BCS'","column_id":"last_prediction"},
                 "color":"#059669","fontWeight":"700"},
                {"if":{"filter_query":"{last_prediction} = 'Mastectomy'","column_id":"last_prediction"},
                 "color":"#DC2626","fontWeight":"700"},
                {"if":{"filter_query":"{DISEASE} = 'BCS'","column_id":"DISEASE"},
                 "color":"#059669"},
                {"if":{"filter_query":"{DISEASE} = 'Mastectomy'","column_id":"DISEASE"},
                 "color":"#DC2626"},
                {"if":{"state":"selected"},"backgroundColor":"#FDF2F8","border":"none"},
            ],
            style_as_list_view=True,
            export_format="csv",
        ),

        html.Div([
            dbc.Button("🔍  Dettaglio completo", id="btn-detail",
                       className="btn-outline-purple", disabled=True,
                       style={"marginTop":"10px"}),
            dbc.Button("🗑  Elimina", id="btn-del-patient",
                       color="danger", outline=True, disabled=True,
                       style={"marginTop":"10px","borderRadius":"8px","fontWeight":"600"}),
        ], style={"display":"flex","gap":"10px"}),

    ], style={"padding":"20px 24px"}),

    # ── Modal dettaglio completo ───────────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="modal-detail-title")),
        dbc.ModalBody(id="modal-detail-body"),
        dbc.ModalFooter(dbc.Button("Chiudi", id="btn-detail-close",
                                   className="btn-outline-purple")),
    ], id="modal-detail", size="xl", scrollable=True, is_open=False),

    dcc.Store(id="patients-store"),
    html.Div(id="patients-dummy"),
    dcc.Interval(id="patients-init", interval=600, n_intervals=0, max_intervals=1),
])


@callback(
    Output("patients-table","data"),
    Input("pt-search","value"),
    Input("patients-store","data"),
    Input("patients-init","n_intervals"),
)
def load_table(search, _store, _init):
    rows = PatientRepository.get_all(search=search or "")
    for r in rows:
        r["fumo_d"]      = "Sì" if r.get("fumo")      else "No"
        r["menopausa_d"] = "Sì" if r.get("menopausa") else "No"
        r.setdefault("last_prediction", "—")
        r.setdefault("DISEASE", "—")
    return rows


@callback(
    Output("btn-detail","disabled"),
    Output("btn-del-patient","disabled"),
    Input("patients-table","selected_rows"),
)
def toggle_btns(rows):
    d = not bool(rows)
    return d, d


@callback(
    Output("modal-detail","is_open"),
    Output("modal-detail-title","children"),
    Output("modal-detail-body","children"),
    Input("btn-detail","n_clicks"),
    Input("btn-detail-close","n_clicks"),
    State("patients-table","selected_rows"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def toggle_detail(n_open, n_close, sel, data):
    if ctx.triggered_id == "btn-detail-close":
        return False, "", ""
    if not sel:
        return False, "", ""
    row = data[sel[0]]
    pid = row.get("id")
    p   = PatientRepository.get_by_id(pid) or row

    from ml.weka_bridge import FEATURE_LABELS, FEATURE_GROUPS
    sections = []
    for grp, feats in FEATURE_GROUPS.items():
        cards = []
        for f in feats:
            val = p.get(f)
            if val is None: val = "—"
            cards.append(dbc.Col(html.Div([
                html.Div(FEATURE_LABELS.get(f,f),
                         style={"fontSize":"11px","color":"#6B7280","fontWeight":"600"}),
                html.Div(str(val),
                         style={"fontSize":"16px","fontWeight":"700","color":"#1A1A2E"}),
            ], style={"background":"#F4F6F9","borderRadius":"8px","padding":"10px"}),
            md=3, style={"marginBottom":"8px"}))
        sections.append(html.Div([
            html.Div(grp, style={"background":"#F8D7E8","color":PINK,
                                 "fontWeight":"700","fontSize":"12px",
                                 "padding":"6px 14px","borderRadius":"6px",
                                 "marginBottom":"10px","marginTop":"14px"}),
            dbc.Row(cards, className="g-2"),
        ]))

    # DISEASE + predizione AI
    disease = p.get("DISEASE","—")
    pred    = p.get("last_prediction","—")
    d_color = {"BCS":"#059669","Mastectomy":"#DC2626"}.get(disease,"#6B7280")
    p_color = {"BCS":"#059669","Mastectomy":"#DC2626"}.get(pred,"#6B7280")

    header = dbc.Row([
        dbc.Col(html.Div([
            html.Div("Chirurgia effettiva",
                     style={"fontSize":"11px","color":"#6B7280","fontWeight":"600"}),
            html.Div(disease, style={"fontSize":"22px","fontWeight":"800","color":d_color}),
        ], style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}), md=4),
        dbc.Col(html.Div([
            html.Div("Predizione AI",
                     style={"fontSize":"11px","color":"#6B7280","fontWeight":"600"}),
            html.Div(pred, style={"fontSize":"22px","fontWeight":"800","color":p_color}),
        ], style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}), md=4),
        dbc.Col(html.Div([
            html.Div("Codice",
                     style={"fontSize":"11px","color":"#6B7280","fontWeight":"600"}),
            html.Div(p.get("code","—"),
                     style={"fontSize":"22px","fontWeight":"800","color":"#1A1A2E"}),
        ], style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}), md=4),
    ], className="g-2 mb-2")

    return True, f"Paziente {p.get('code','')}", [header] + sections


@callback(
    Output("patients-dummy","children"),
    Input("btn-del-patient","n_clicks"),
    State("patients-table","selected_rows"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def delete_patient(n, sel, data):
    if n and sel:
        PatientRepository.delete(int(data[sel[0]].get("id")))
    return ""


# ── Modal nuovo paziente ───────────────────────────────────────────────────────
# (form completo con tutte e 22 le feature)
@callback(
    Output("patients-store","data"),
    Input("patients-dummy","children"),
)
def refresh_store(_):
    return str(__import__("time").time())
