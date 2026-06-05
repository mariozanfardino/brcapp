import dash
from dash import html, dcc, dash_table, callback, Output, Input, State, ALL, ctx
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from config import PINK, PURPLE, PINK_L, PURP_L

dash.register_page(__name__, path="/patients", name="Pazienti")

COLS = [
    {"name":"Codice",      "id":"code",            "type":"text"},
    {"name":"Età",         "id":"age",             "type":"numeric"},
    {"name":"BMI",         "id":"bmi",             "type":"numeric"},
    {"name":"Tumore (mm)", "id":"tumor_size_mm",   "type":"numeric"},
    {"name":"Grado",       "id":"grade",           "type":"numeric"},
    {"name":"ER",          "id":"er_display",      "type":"text"},
    {"name":"PR",          "id":"pr_display",      "type":"text"},
    {"name":"HER2",        "id":"her2_display",    "type":"text"},
    {"name":"Pred. AI",    "id":"last_prediction", "type":"text"},
    {"name":"Aggiunto",    "id":"created_at",      "type":"text"},
]

def _opt(label, key, opts, row=0, col=0):
    return dbc.Col([
        dbc.Label(label, className="form-label"),
        dbc.Select(options=[{"label":o,"value":o} for o in opts],
                   id={"type":"pf","key":key}, value=opts[0])
    ], md=6)

def _inp(label, key, placeholder="", type="text"):
    return dbc.Col([
        dbc.Label(label, className="form-label"),
        dbc.Input(id={"type":"pf","key":key},
                  placeholder=placeholder, type=type)
    ], md=6)

def _num(label, key, min=0, max=999, step=0.1, val=0):
    return dbc.Col([
        dbc.Label(label, className="form-label"),
        dbc.Input(id={"type":"pf","key":key}, type="number",
                  min=min, max=max, step=step, value=val)
    ], md=6)

def _bool_sel(label, key):
    return dbc.Col([
        dbc.Label(label, className="form-label"),
        dbc.Select(options=[{"label":"No","value":"0"},{"label":"Sì","value":"1"}],
                   id={"type":"pf","key":key}, value="0")
    ], md=6)

layout = html.Div([
    # Topbar
    html.Div([
        html.Div([
            html.H1("Archivio Pazienti", className="page-title"),
            html.P("Gestione completa pazienti", className="page-subtitle"),
        ]),
        html.Div([
            dbc.Input(id="pt-search", placeholder="  Cerca paziente…",
                      debounce=True, style={"width":"250px","height":"38px",
                                            "borderRadius":"8px","fontSize":"13px"}),
            dbc.Button("＋  Nuovo Paziente", id="btn-new-patient",
                       className="btn-pink"),
            html.A(
                dbc.Button("🔑  Genera PIN accesso", className="btn-outline-purple"),
                href="/admin/pins",
                style={"textDecoration":"none"},
            ),
        ], style={"display":"flex","gap":"10px","alignItems":"center"}),
    ], className="page-topbar"),

    html.Div([
        dash_table.DataTable(
            id="patients-table",
            columns=COLS,
            data=[],
            row_selectable="single",
        sort_action="native",
        sort_mode="multi",
            selected_rows=[],
            style_table={"borderRadius":"12px","overflow":"hidden",
                         "border":"1px solid #E5E7EB"},
            style_cell={"textAlign":"left","padding":"11px 14px",
                        "fontSize":"13px","fontFamily":"Inter,Arial,sans-serif",
                        "border":"none","borderBottom":"1px solid #F3F4F6"},
            style_header={"backgroundColor":"#EDE7F6","color":"#4A235A",
                          "fontWeight":"700","fontSize":"11px",
                          "textTransform":"uppercase","letterSpacing":"0.5px",
                          "border":"none","borderBottom":"1px solid #E5E7EB"},
            style_data_conditional=[
                {"if":{"filter_query":"{last_prediction} = 'BCS'",
                        "column_id":"last_prediction"},
                 "color":"#059669","fontWeight":"700"},
                {"if":{"filter_query":"{last_prediction} = 'Mastectomy'",
                        "column_id":"last_prediction"},
                 "color":"#DC2626","fontWeight":"700"},
                {"if":{"state":"selected"},"backgroundColor":"#FDF2F8",
                 "border":"none"},
            ],
            style_as_list_view=True,
            page_size=20,
        ),

        # Row action bar
        html.Div([
            dbc.Button("✏  Modifica selezionato", id="btn-edit-patient",
                       className="btn-outline-purple", disabled=True),
            dbc.Button("🗑  Elimina", id="btn-del-patient",
                       color="danger", outline=True, disabled=True,
                       style={"borderRadius":"8px","fontWeight":"600"}),
        ], style={"display":"flex","gap":"10px","marginTop":"12px"}),

    ], style={"padding":"20px 24px"}),

    # ── Modal Form ────────────────────────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Scheda Paziente", id="modal-pt-title")),
        dbc.ModalBody([
            dcc.Store(id="editing-patient-id", data=None),

            html.Div("🧑  Anagrafica", className="form-section"),
            dbc.Row([
                _inp("Codice paziente *","code"),
                _inp("Iniziali","initials"),
            ], className="g-2 mb-2"),
            dbc.Row([
                _num("Età (anni) *","age", min=18, max=100, step=1, val=50),
                _num("BMI *","bmi", min=10, max=60, step=0.1, val=25.0),
            ], className="g-2 mb-2"),

            html.Div("🔬  Dati Clinici", className="form-section"),
            dbc.Row([
                _num("Diametro tumore (mm) *","tumor_size_mm", min=1, max=200, step=0.5, val=20),
                _opt("Quadrante","tumor_quadrant",
                     ["1-SUE","2-SUI","3-SLE","4-SLI","5-Centrale"]),
            ], className="g-2 mb-2"),
            dbc.Row([
                _opt("Istologia","histology_type",["1-IDC","2-ILC","3-Altro"]),
                _opt("Grado (G)","grade",["1","2","3"]),
            ], className="g-2 mb-2"),
            dbc.Row([
                _bool_sel("ER","er_status"),
                _bool_sel("PR","pr_status"),
            ], className="g-2 mb-2"),
            dbc.Row([
                _bool_sel("HER2","her2_status"),
                _num("Ki67 (%)","ki67_percent", min=0, max=100, step=1, val=20),
            ], className="g-2 mb-2"),
            dbc.Row([
                _bool_sel("Multifocalità","multifocality"),
                _bool_sel("Linfonodi positivi","lymph_node_positive"),
            ], className="g-2 mb-2"),
            dbc.Row([
                _opt("Chirurgia effettiva","actual_surgery",
                     ["Non eseguita","BCS","Mastectomy"]),
            ], className="g-2 mb-2"),

            html.Div("🥗  Stile di Vita", className="form-section"),
            dbc.Row([
                _num("Score alimentare (0-10)*","eating_habit_score",min=0,max=10,step=0.5,val=5),
                _num("Attività fisica (0-10)*","physical_activity",min=0,max=10,step=0.5,val=5),
            ], className="g-2 mb-2"),
            dbc.Row([
                _bool_sel("Fumo","smoking"),
                _bool_sel("Alcool","alcohol"),
            ], className="g-2 mb-2"),
            dbc.Row([
                _bool_sel("Dieta Mediterranea","mediterranean_diet"),
            ], className="g-2 mb-2"),

            html.Div("📝  Note", className="form-section"),
            dbc.Textarea(id={"type":"pf","key":"notes"}, rows=3,
                         style={"borderRadius":"7px","fontSize":"13px"}),

            html.Div(id="form-error",
                     style={"color":"#DC2626","fontSize":"13px","marginTop":"8px"}),
        ]),
        dbc.ModalFooter([
            dbc.Button("Annulla", id="btn-modal-cancel",
                       className="btn-outline-purple"),
            dbc.Button("💾  Salva paziente", id="btn-modal-save",
                       className="btn-pink"),
        ]),
    ], id="modal-patient", size="lg", is_open=False, scrollable=True),

    dcc.Store(id="patients-store"),
    html.Div(id="patients-dummy"),
    # Forza caricamento tabella all'avvio
    dcc.Interval(id="patients-init", interval=500, n_intervals=0, max_intervals=1),
])


# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("patients-table","data"),
    Input("pt-search","value"),
    Input("patients-store","data"),
    Input("patients-init","n_intervals"),
)
def load_table(search, _store, _init):
    rows = PatientRepository.get_all(search=search or "")
    for r in rows:
        r["er_display"]   = "＋" if r.get("er_status")   else "－"
        r["pr_display"]   = "＋" if r.get("pr_status")   else "－"
        r["her2_display"] = "＋" if r.get("her2_status") else "－"
        r.setdefault("last_prediction","—")
    return rows


@callback(
    Output("btn-edit-patient","disabled"),
    Output("btn-del-patient","disabled"),
    Input("patients-table","selected_rows"),
)
def toggle_row_btns(rows):
    disabled = not rows
    return disabled, disabled


@callback(
    Output("modal-patient","is_open"),
    Output("modal-pt-title","children"),
    Output("editing-patient-id","data"),
    Output({"type":"pf","key":"code"},"value"),
    Output({"type":"pf","key":"initials"},"value"),
    Output({"type":"pf","key":"age"},"value"),
    Output({"type":"pf","key":"bmi"},"value"),
    Output({"type":"pf","key":"tumor_size_mm"},"value"),
    Output({"type":"pf","key":"ki67_percent"},"value"),
    Output({"type":"pf","key":"eating_habit_score"},"value"),
    Output({"type":"pf","key":"physical_activity"},"value"),
    Output({"type":"pf","key":"notes"},"value"),
    Input("btn-new-patient","n_clicks"),
    Input("btn-edit-patient","n_clicks"),
    Input("btn-modal-cancel","n_clicks"),
    Input("btn-modal-save","n_clicks"),
    State("patients-table","selected_rows"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def toggle_modal(n_new, n_edit, n_cancel, n_save, sel_rows, table_data):
    blank = (False,"Scheda Paziente",None,"","",50,25.0,20,20,5,5,"")
    trigger = ctx.triggered_id
    if trigger in ("btn-modal-cancel","btn-modal-save"):
        return blank
    if trigger == "btn-new-patient":
        return (True,"Nuovo Paziente",None,"","",50,25.0,20,20,5,5,"")
    if trigger == "btn-edit-patient" and sel_rows:
        row = table_data[sel_rows[0]]
        pid = row.get("id")
        p   = PatientRepository.get_by_id(pid) or {}
        return (True, f"Modifica — {p.get('code','')}",
                pid,
                p.get("code",""), p.get("initials",""),
                p.get("age",50), p.get("bmi",25.0),
                p.get("tumor_size_mm",20), p.get("ki67_percent",20),
                p.get("eating_habit_score",5), p.get("physical_activity",5),
                p.get("notes",""))
    return blank


@callback(
    Output("patients-store","data"),
    Output("form-error","children"),
    Input("btn-modal-save","n_clicks"),
    State("editing-patient-id","data"),
    State({"type":"pf","key":ALL},"value"),
    State({"type":"pf","key":ALL},"id"),
    prevent_initial_call=True,
)
def save_patient(n_clicks, pid, values, ids):
    if not n_clicks:
        return dash.no_update, ""
    data = {i["key"]: v for i, v in zip(ids, values)}
    if not data.get("code","").strip():
        return dash.no_update, "Il codice paziente è obbligatorio."
    try:
        def intpfx(k):
            v = str(data.get(k,"1"))
            return int(v.split("-")[0])
        payload = {
            "code":    str(data.get("code","")).strip(),
            "initials":str(data.get("initials","")).strip(),
            "age":     int(float(data.get("age") or 50)),
            "bmi":     float(data.get("bmi") or 25),
            "tumor_size_mm":   float(data.get("tumor_size_mm") or 20),
            "tumor_quadrant":  intpfx("tumor_quadrant"),
            "histology_type":  intpfx("histology_type"),
            "grade":           intpfx("grade"),
            "er_status":       data.get("er_status","0") == "1",
            "pr_status":       data.get("pr_status","0") == "1",
            "her2_status":     data.get("her2_status","0") == "1",
            "ki67_percent":    float(data.get("ki67_percent") or 0),
            "multifocality":         data.get("multifocality","0") == "1",
            "lymph_node_positive":   data.get("lymph_node_positive","0") == "1",
            "actual_surgery":        str(data.get("actual_surgery","Non eseguita")).split("-")[0],
            "eating_habit_score":    float(data.get("eating_habit_score") or 5),
            "physical_activity":     float(data.get("physical_activity") or 5),
            "smoking":               data.get("smoking","0") == "1",
            "alcohol":               data.get("alcohol","0") == "1",
            "mediterranean_diet":    data.get("mediterranean_diet","0") == "1",
            "notes":                 str(data.get("notes","") or ""),
        }
        if pid:
            PatientRepository.update(int(pid), payload)
        else:
            PatientRepository.create(payload)
        return str(n_clicks), ""
    except Exception as e:
        return dash.no_update, f"Errore: {e}"


@callback(
    Output("patients-dummy","children"),
    Input("btn-del-patient","n_clicks"),
    State("patients-table","selected_rows"),
    State("patients-table","data"),
    prevent_initial_call=True,
)
def delete_patient(n, sel_rows, table_data):
    if n and sel_rows:
        pid = table_data[sel_rows[0]].get("id")
        if pid: PatientRepository.delete(int(pid))
    return ""
