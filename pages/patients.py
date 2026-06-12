import dash
from dash import html, dcc, callback, Output, Input, State, ctx
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from config import PINK, PURPLE

dash.register_page(__name__, path="/patients", name="Pazienti")

MAIN_COLS = [
    {"name":"Codice",           "id":"code"},
    {"name":"Età",              "id":"age_range"},
    {"name":"Sesso",            "id":"gender"},
    {"name":"Nazionalità",      "id":"nazionalita"},
    {"name":"Gruppo sang.",     "id":"blood_display"},
    {"name":"BI-RADS",          "id":"biRadsClinico"},
    {"name":"Focalità",         "id":"focalita"},
    {"name":"Classificazione AI","id":"last_prediction"},
    {"name":"DISEASE",          "id":"DISEASE"},
]

SECTIONS = {
    "📊 Vital Statistics": [
        ("Codice","code"),("Sesso","gender"),("Nazionalità","nazionalita"),
        ("Data nascita","birth_date"),("Fascia età","age_range"),
        ("Gruppo sang.","blood_display"),
    ],
    "📋 Clinical History": [
        ("Peso (kg)","peso"),("Altezza (cm)","altezza"),("BMI","bmi"),
        ("Vita (cm)","waist"),("Fianchi (cm)","hips"),("WHR","whr"),
        ("Fumo","fumo"),("Alcool","alcohol"),("Gravidanza","gravidanza"),
        ("Mutazione BRCA","brca_mutation"),("Familiarità K.ovaio","familiarita_carcinoma_ovarico"),
        ("K. pregresso","previous_cancer"),("K. mammella prec.","previous_breast_cancer"),
        ("Chemioterapia prec.","previous_chemotherapy"),("Radioterapia prec.","previous_radiotherapy"),
        ("Chirurgie mammarie prec.","breast_surgeries"),
        ("Malattie autoimmuni","autoimmune_diseases"),("Diabete","diabetes"),
        ("Cheloidi","keloids"),("Familiarità K.mammella","familial_breast_cancer"),
        ("Taglia reggiseno","bra_size"),("Grado ptosi","ptosis_degree"),
        ("Tropismo cutaneo","skin_tropism"),("Struttura ghiandolare","struttura_ghiandolare"),
    ],
    "🔬 Clinical Data": [
        ("Chemio preop.","preoperative_chemotherapy"),("Tipo lesione","injury_type"),
        ("Sede cancro","cancer_site"),("Dimensione tumore (mm)","tumor_size_mm"),
        ("N. lesioni","injuries_number"),("Focalità","focalita"),
        ("Cute DX","rapporto_cuteDX"),("Cute SX","rapporto_cuteSX"),
        ("Areola-capezzolo DX","rapporto_areola_capezzoloDX"),
        ("Areola-capezzolo SX","rapporto_areola_capezzoloSX"),
        ("Evento","event"),("Lesioni dubbie","dubious_injuries"),
        ("Sede principale","main_cancer_site"),("Componente in situ","tumor_in_situ"),
    ],
    "🎗 Breast Cancer Evaluation": [
        ("Istotipo","histotype"),("Grading","grading"),("Stadio clinico","clinical_stage"),
        ("ER","er_status"),("PgR","pgr_status"),("Ki-67 (%)","ki67"),
        ("CerbB2","cerbb2"),("Classificazione","classification_pre"),
        ("Stato linfonodale DX","stato_linfonodaleDX"),("Stato linfonodale SX","stato_linfonodaleSX"),
        ("BI-RADS clinico","biRadsClinico"),("Citologia","citologia_codifica"),
        ("Ricostruzione pianif.","ricostruzione"),
    ],
    "🏥 Pre/Post Treatment": [
        ("Tipo op. T","t_operation_type"),("Tipo op. N","n_operation_type"),
        ("Istotipo post-op","histotype_post"),("Grading post-op","grading_post"),
        ("Stadio post-op","clinical_stage_post"),("ER post-op","er_post"),
        ("PgR post-op","pgr_post"),("Ki-67 post-op","ki67_post"),
        ("CerbB2 post-op","cerbb2_post"),("Classificazione post-op","classification_post"),
        ("Stato linfonodale post-op","nodal_status_post"),
        ("Andamento chirurgico","surgical_progress"),
        ("Risultato cosmetico/funz.","cosmetic_result"),("DISEASE (outcome)","DISEASE"),
    ],
}


def _section_grid(fields, p):
    items = []
    for label, key in fields:
        val = p.get(key)
        if val is None or val == "": val = "—"
        color = "#1A1A2E"
        if key in ("last_prediction","DISEASE"):
            color = {"CONSERVATIVA":"#059669","MASTECTOMIA":"#DC2626"}.get(str(val),"#6B7280")
        items.append(dbc.Col(html.Div([
            html.Div(label, style={"fontSize":"10px","color":"#9CA3AF","fontWeight":"600",
                                   "textTransform":"uppercase","letterSpacing":"0.4px",
                                   "marginBottom":"4px"}),
            html.Div(str(val), style={"fontSize":"14px","fontWeight":"600","color":color}),
        ], style={"background":"#F8F9FA","borderRadius":"8px","padding":"10px 14px"}),
        md=3, style={"marginBottom":"8px"}))
    return dbc.Row(items, className="g-2")


layout = html.Div([
    html.Div([
        html.Div([html.H1("Archivio Pazienti",className="page-title"),
                  html.P("Click su riga → scheda clinica completa",className="page-subtitle")]),
        dbc.Input(id="pt-search",placeholder="  Cerca codice…",debounce=True,
                  style={"width":"220px","height":"38px","borderRadius":"8px","fontSize":"13px"}),
    ], className="page-topbar"),

    html.Div([
        html.Div("💡  Clicca su una riga per aprire la scheda clinica",
                 style={"fontSize":"12px","color":"#6B7280","marginBottom":"10px"}),
        dash.dash_table.DataTable(
            id="patients-table", columns=MAIN_COLS, data=[],
            row_selectable="single", selected_rows=[],
            sort_action="native", sort_mode="multi",
            filter_action="native", page_size=20,
            style_table={"borderRadius":"12px","overflow":"hidden","border":"1px solid #E5E7EB"},
            style_cell={"textAlign":"left","padding":"11px 14px","fontSize":"13px",
                        "fontFamily":"Inter,Arial,sans-serif","border":"none",
                        "borderBottom":"1px solid #F3F4F6","cursor":"pointer"},
            style_header={"backgroundColor":"#EDE7F6","color":"#4A235A","fontWeight":"700",
                          "fontSize":"11px","textTransform":"uppercase","letterSpacing":"0.5px",
                          "border":"none","borderBottom":"1px solid #E5E7EB"},
            style_data_conditional=[
                {"if":{"filter_query":"{last_prediction} = 'CONSERVATIVA'","column_id":"last_prediction"},"color":"#059669","fontWeight":"700"},
                {"if":{"filter_query":"{last_prediction} = 'MASTECTOMIA'","column_id":"last_prediction"},"color":"#DC2626","fontWeight":"700"},
                {"if":{"filter_query":"{DISEASE} = 'CONSERVATIVA'","column_id":"DISEASE"},"color":"#059669"},
                {"if":{"filter_query":"{DISEASE} = 'MASTECTOMIA'","column_id":"DISEASE"},"color":"#DC2626"},
                {"if":{"state":"selected"},"backgroundColor":"#FDF2F8","border":"none"},
            ],
            style_as_list_view=True, export_format="csv",
        ),
        html.Div(id="pt-row-count",style={"fontSize":"12px","color":"#9CA3AF","marginTop":"8px"}),
    ], style={"padding":"20px 24px"}),

    # ── Modal scheda paziente con TAB ─────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(html.Div(id="modal-pt-header"),
                        style={"background":f"linear-gradient(135deg,{PINK},{PURPLE})",
                               "borderRadius":"12px 12px 0 0"}),
        dbc.ModalBody([
            dbc.Tabs([
                dbc.Tab(label="📊 Vital Statistics",    tab_id="vs"),
                dbc.Tab(label="📋 Clinical History",   tab_id="ch"),
                dbc.Tab(label="🔬 Clinical Data",      tab_id="cd"),
                dbc.Tab(label="🎗 Breast Evaluation",  tab_id="be"),
                dbc.Tab(label="🏥 Pre/Post Treatment", tab_id="pp"),
            ], id="pt-modal-tabs", active_tab="vs",
               style={"marginBottom":"16px"}),
            html.Div(id="pt-modal-tab-content"),
        ]),
        dbc.ModalFooter([
            dbc.Button("🚀  Classifica questo paziente", id="btn-classify-from-pt",
                       className="btn-pink"),
            dbc.Button("📊  Vedi XAI", id="btn-xai-from-pt",
                       className="btn-outline-purple"),
            dbc.Button("Chiudi", id="btn-pt-close", color="light",
                       style={"borderRadius":"8px"}),
        ]),
    ], id="modal-patient-detail", size="xl", scrollable=True, is_open=False),

    dcc.Store(id="patients-store"),
    dcc.Store(id="selected-patient-id"),
    dcc.Location(id="pt-nav"),
    dcc.Interval(id="patients-init", interval=600, n_intervals=0, max_intervals=1),
])


@callback(
    Output("patients-table","data"), Output("pt-row-count","children"),
    Input("pt-search","value"), Input("patients-store","data"),
    Input("patients-init","n_intervals"),
)
def load_table(search,_,__):
    rows = PatientRepository.get_all(search=search or "")
    for r in rows:
        r["blood_display"] = (f"{r.get('blood_type','?')} {'Rh+' if r.get('rh_positive') else 'Rh-'}"
                              if r.get("blood_type") else "—")
        r.setdefault("last_prediction","—")
        r.setdefault("DISEASE","—")
        r.setdefault("focalita","—")
        r.setdefault("biRadsClinico","—")
    return rows, f"{len(rows)} pazienti"


@callback(
    Output("modal-patient-detail","is_open"),
    Output("modal-pt-header","children"),
    Output("selected-patient-id","data"),
    Input("patients-table","selected_rows"),
    Input("btn-pt-close","n_clicks"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def open_modal(sel, n_close, table_data):
    if ctx.triggered_id == "btn-pt-close" or not sel:
        return False, "", None
    row = table_data[sel[0]]
    pid = int(row["id"])
    p   = PatientRepository.get_by_id(pid) or row

    pred  = p.get("last_prediction","—")
    p_col = {"CONSERVATIVA":"#059669","MASTECTOMIA":"#DC2626"}.get(pred,"#aaa")

    header = html.Div([
        html.Div([
            html.Div(p.get("code",""), style={"fontSize":"22px","fontWeight":"800","color":"white"}),
            html.Div(f"{p.get('age_range','—')}  ·  {p.get('gender','F')}  ·  {p.get('nazionalita','Italiana')}",
                     style={"fontSize":"13px","color":"rgba(255,255,255,.8)","marginTop":"4px"}),
        ], style={"flex":"1"}),
        html.Div([
            html.Div("Classificazione AI",
                     style={"fontSize":"10px","color":"rgba(255,255,255,.7)","marginBottom":"2px"}),
            html.Div(pred, style={"fontSize":"16px","fontWeight":"800","color":"white",
                                   "background":"rgba(255,255,255,.2)","padding":"4px 14px",
                                   "borderRadius":"20px","display":"inline-block"}),
        ]),
    ], style={"display":"flex","alignItems":"center","gap":"20px"})

    return True, header, pid


@callback(
    Output("pt-modal-tab-content","children"),
    Input("pt-modal-tabs","active_tab"),
    State("selected-patient-id","data"),
    prevent_initial_call=True,
)
def render_tab(tab, pid):
    if not pid: return html.Div()
    p = PatientRepository.get_by_id(int(pid)) or {}
    p["blood_display"] = (f"{p.get('blood_type','?')} {'Rh+' if p.get('rh_positive') else 'Rh-'}"
                          if p.get("blood_type") else "—")
    tab_map = {"vs":"📊 Vital Statistics","ch":"📋 Clinical History",
               "cd":"🔬 Clinical Data","be":"🎗 Breast Cancer Evaluation",
               "pp":"🏥 Pre/Post Treatment"}
    sec_name = tab_map.get(tab)
    if not sec_name or sec_name not in SECTIONS:
        return html.Div()
    return _section_grid(SECTIONS[sec_name], p)


@callback(
    Output("btn-classify-from-pt","disabled"),
    Output("btn-classify-from-pt","title"),
    Input("selected-patient-id","data"),
)
def toggle_classify_btn(pid):
    if not pid: return True, ""
    p = PatientRepository.get_by_id(int(pid)) or {}
    already = bool(p.get("last_prediction") and p["last_prediction"] not in (None,"—",""))
    return already, ("Paziente già classificato" if already else "Esegui classificazione AI")


@callback(Output("pt-nav","href"),
          Input("btn-classify-from-pt","n_clicks"),
          prevent_initial_call=True)
def go_classify(_): return "/classification"


@callback(Output("pt-nav","href","allow_duplicate"),
          Input("btn-xai-from-pt","n_clicks"),
          prevent_initial_call=True)
def go_xai(_): return "/xai"


@callback(Output("patients-store","data"),
          Input("patients-init","n_intervals"))
def init_store(_):
    import time; return str(time.time())
