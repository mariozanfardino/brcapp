import dash
from dash import html, dcc, dash_table, callback, Output, Input, State, ctx
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from config import PINK, PURPLE

dash.register_page(__name__, path="/patients", name="Pazienti")

# ── Colonne principali in tabella ─────────────────────────────────────────────
MAIN_COLS = [
    {"name":"Codice",          "id":"code"},
    {"name":"Età",             "id":"age_range"},
    {"name":"Sesso",           "id":"gender"},
    {"name":"Nazionalità",     "id":"nazionalita"},
    {"name":"Gruppo sang.",    "id":"blood_display"},
    {"name":"BI-RADS",         "id":"biRadsClinico"},
    {"name":"Focalità",        "id":"focalita"},
    {"name":"Classificazione AI","id":"last_prediction"},
    {"name":"DISEASE",         "id":"DISEASE"},
]

# ── Sezioni della scheda paziente completa ────────────────────────────────────
SECTIONS = {
    "📊  Vital Statistics": [
        ("Codice paziente","code"),("Sesso","gender"),("Nazionalità","nazionalita"),
        ("Data di nascita","birth_date"),("Fascia età","age_range"),
        ("Gruppo sanguigno","blood_display"),
    ],
    "📋  Clinical History": [
        ("Peso (kg)","peso"),("Altezza (cm)","altezza"),("BMI","bmi"),
        ("Vita (cm)","waist"),("Fianchi (cm)","hips"),("WHR","whr"),
        ("Fumo","fumo"),("Alcool","alcohol"),("Gravidanza","gravidanza"),
        ("K. ovaio in famiglia","familiarita_carcinoma_ovarico"),
        ("K. pregresso","previous_cancer"),("K. mammella prec.","previous_breast_cancer"),
        ("Chemioterapia prec.","previous_chemotherapy"),
        ("Radioterapia prec.","previous_radiotherapy"),
        ("Chirurgie mammarie prec.","breast_surgeries"),
        ("Malattie autoimmuni","autoimmune_diseases"),("Diabete","diabetes"),
        ("Cheloidi","keloids"),("Familiarità K. mammella","familial_breast_cancer"),
        ("Mutazione BRCA","brca_mutation"),("Taglia reggiseno","bra_size"),
        ("Grado ptosi","ptosis_degree"),("Tropismo cutaneo","skin_tropism"),
        ("Struttura ghiandolare","struttura_ghiandolare"),
    ],
    "🔬  Clinical Data": [
        ("Chemioterapia preop.","preoperative_chemotherapy"),
        ("Tipo lesione","injury_type"),("Sede cancro","cancer_site"),
        ("Dimensione tumore (mm)","tumor_size_mm"),("N. lesioni","injuries_number"),
        ("Focalità","focalita"),("Cute DX","rapporto_cuteDX"),
        ("Cute SX","rapporto_cuteSX"),
        ("Areola-capezzolo DX","rapporto_areola_capezzoloDX"),
        ("Areola-capezzolo SX","rapporto_areola_capezzoloSX"),
        ("Evento","event"),("Lesioni dubbie concomitanti","dubious_injuries"),
        ("Sede principale","main_cancer_site"),("Componente in situ","tumor_in_situ"),
    ],
    "🎗  Specific Breast Cancer Evaluation": [
        ("Istotipo","histotype"),("Grading","grading"),
        ("Stadio clinico","clinical_stage"),
        ("ER","er_status"),("PgR","pgr_status"),
        ("Ki-67 (%)","ki67"),("CerbB2","cerbb2"),
        ("Classificazione","classification_pre"),
        ("Stato linfonodale DX","stato_linfonodaleDX"),
        ("Stato linfonodale SX","stato_linfonodaleSX"),
        ("BI-RADS clinico","biRadsClinico"),
        ("Citologia","citologia_codifica"),
        ("Ricostruzione pianificata","ricostruzione"),
    ],
    "🏥  Pre/Post Treatment Diagnosis": [
        ("Tipo operazione T","t_operation_type"),
        ("Tipo operazione N","n_operation_type"),
        ("Istotipo post-op","histotype_post"),("Grading post-op","grading_post"),
        ("Stadio clinico post-op","clinical_stage_post"),
        ("ER post-op","er_post"),("PgR post-op","pgr_post"),
        ("Ki-67 post-op (%)","ki67_post"),("CerbB2 post-op","cerbb2_post"),
        ("Classificazione post-op","classification_post"),
        ("Stato linfonodale post-op","nodal_status_post"),
        ("Andamento chirurgico","surgical_progress"),
        ("Risultato cosmetico/funzionale","cosmetic_result"),
        ("DISEASE (outcome)","DISEASE"),
    ],
}

layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Archivio Pazienti", className="page-title"),
            html.P("Tabella principale · click su riga per scheda completa",
                   className="page-subtitle"),
        ]),
        html.Div([
            dbc.Input(id="pt-search", placeholder="  Cerca codice…",
                      debounce=True, style={"width":"220px","height":"38px",
                                            "borderRadius":"8px","fontSize":"13px"}),
        ], style={"display":"flex","gap":"10px","alignItems":"center"}),
    ], className="page-topbar"),

    html.Div([
        # Legenda
        html.Div([
            html.Span("💡  Clicca su una riga per visualizzare la scheda clinica completa",
                      style={"fontSize":"12px","color":"#6B7280"}),
        ], style={"marginBottom":"10px"}),

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
            style_table={"borderRadius":"12px","overflow":"hidden",
                         "border":"1px solid #E5E7EB"},
            style_cell={"textAlign":"left","padding":"11px 14px","fontSize":"13px",
                        "fontFamily":"Inter,Arial,sans-serif","border":"none",
                        "borderBottom":"1px solid #F3F4F6","cursor":"pointer"},
            style_header={"backgroundColor":"#EDE7F6","color":"#4A235A",
                          "fontWeight":"700","fontSize":"11px",
                          "textTransform":"uppercase","letterSpacing":"0.5px",
                          "border":"none","borderBottom":"1px solid #E5E7EB"},
            style_data_conditional=[
                {"if":{"filter_query":"{last_prediction} = 'CONSERVATIVA'",
                        "column_id":"last_prediction"},
                 "color":"#059669","fontWeight":"700"},
                {"if":{"filter_query":"{last_prediction} = 'MASTECTOMIA'",
                        "column_id":"last_prediction"},
                 "color":"#DC2626","fontWeight":"700"},
                {"if":{"filter_query":"{DISEASE} = 'CONSERVATIVA'",
                        "column_id":"DISEASE"},
                 "color":"#059669"},
                {"if":{"filter_query":"{DISEASE} = 'MASTECTOMIA'",
                        "column_id":"DISEASE"},
                 "color":"#DC2626"},
                {"if":{"state":"selected"},
                 "backgroundColor":"#FDF2F8","border":"none"},
            ],
            style_as_list_view=True,
            export_format="csv",
        ),
        html.Div(id="pt-row-count",
                 style={"fontSize":"12px","color":"#9CA3AF","marginTop":"8px"}),
    ], style={"padding":"20px 24px"}),

    # ── Modal scheda paziente completa ─────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader([
            html.Div(id="modal-pt-header"),
        ], style={"background":f"linear-gradient(135deg,{PINK},{PURPLE})",
                  "borderRadius":"12px 12px 0 0"}),
        dbc.ModalBody(id="modal-pt-body", style={"padding":"24px"}),
        dbc.ModalFooter([
            dbc.Button("✂️  Classifica questo paziente", id="btn-classify-from-pt",
                       className="btn-pink"),
            dbc.Button("Chiudi", id="btn-pt-close",
                       className="btn-outline-purple"),
        ]),
    ], id="modal-patient-detail", size="xl", scrollable=True, is_open=False),

    dcc.Store(id="patients-store"),
    dcc.Location(id="pt-nav"),
    dcc.Interval(id="patients-init", interval=600, n_intervals=0, max_intervals=1),
])


@callback(
    Output("patients-table","data"),
    Output("pt-row-count","children"),
    Input("pt-search","value"),
    Input("patients-store","data"),
    Input("patients-init","n_intervals"),
)
def load_table(search, _store, _init):
    rows = PatientRepository.get_all(search=search or "")
    for r in rows:
        r["blood_display"] = (
            f"{r.get('blood_type','?')} {'Rh+' if r.get('rh_positive') else 'Rh-'}"
            if r.get("blood_type") else "—"
        )
        r.setdefault("last_prediction","—")
        r.setdefault("DISEASE","—")
        r.setdefault("focalita","—")
        r.setdefault("biRadsClinico","—")
    return rows, f"{len(rows)} pazienti"


@callback(
    Output("modal-patient-detail","is_open"),
    Output("modal-pt-header","children"),
    Output("modal-pt-body","children"),
    Input("patients-table","selected_rows"),
    Input("btn-pt-close","n_clicks"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def open_patient_card(sel_rows, n_close, table_data):
    if ctx.triggered_id == "btn-pt-close" or not sel_rows:
        return False, "", ""

    row = table_data[sel_rows[0]]
    p   = PatientRepository.get_by_id(int(row["id"])) or row

    # Header
    pred  = p.get("last_prediction","—")
    p_col = {"CONSERVATIVA":"#059669","MASTECTOMIA":"#DC2626"}.get(pred,"#fff")
    header = html.Div([
        html.Div([
            html.Div(p.get("code",""), style={"fontSize":"22px","fontWeight":"800",
                                               "color":"white"}),
            html.Div([
                html.Span(f"{p.get('age_range','—')} anni  ·  {p.get('gender','F')}  ·  "
                          f"{p.get('nazionalita','Italiana')}",
                          style={"fontSize":"13px","color":"rgba(255,255,255,0.85)"}),
            ]),
        ], style={"flex":"1"}),
        html.Div([
            html.Div("Classificazione AI",
                     style={"fontSize":"11px","color":"rgba(255,255,255,0.7)",
                            "marginBottom":"2px"}),
            html.Div(pred, style={"fontSize":"18px","fontWeight":"800",
                                   "color":"white",
                                   "background":"rgba(255,255,255,0.2)",
                                   "padding":"4px 14px","borderRadius":"20px"}),
        ]),
    ], style={"display":"flex","alignItems":"center","gap":"20px"})

    # Body — sezioni
    sections_html = []
    for sec_title, fields in SECTIONS.items():
        items = []
        for label, key in fields:
            val = p.get(key)
            if val is None or val == "": val = "—"
            # Colore per valori chiave
            color = "#1A1A2E"
            if key == "last_prediction":
                color = {"CONSERVATIVA":"#059669","MASTECTOMIA":"#DC2626"}.get(str(val),"#1A1A2E")
            if key == "DISEASE":
                color = {"CONSERVATIVA":"#059669","MASTECTOMIA":"#DC2626"}.get(str(val),"#6B7280")
            items.append(dbc.Col(html.Div([
                html.Div(label, style={"fontSize":"10px","color":"#9CA3AF",
                                       "fontWeight":"600","textTransform":"uppercase",
                                       "letterSpacing":"0.5px","marginBottom":"3px"}),
                html.Div(str(val), style={"fontSize":"14px","fontWeight":"600",
                                          "color":color}),
            ], style={"background":"#F8F9FA","borderRadius":"8px",
                      "padding":"10px 12px"}), md=3, style={"marginBottom":"8px"}))

        sections_html.append(html.Div([
            html.Div(sec_title,
                     style={"background":f"linear-gradient(90deg,{PINK}22,transparent)",
                            "color":PINK,"fontWeight":"700","fontSize":"13px",
                            "padding":"8px 16px","borderRadius":"8px",
                            "borderLeft":f"4px solid {PINK}",
                            "marginBottom":"12px","marginTop":"20px"}),
            dbc.Row(items, className="g-2"),
        ]))

    return True, header, html.Div(sections_html)


@callback(
    Output("pt-nav","href"),
    Input("btn-classify-from-pt","n_clicks"),
    prevent_initial_call=True,
)
def go_classify(_):
    return "/classification"


@callback(
    Output("patients-store","data"),
    Input("patients-init","n_intervals"),
)
def init_store(_):
    import time
    return str(time.time())
