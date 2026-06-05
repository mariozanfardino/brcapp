import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from dash import dash_table
from database.db import PatientRepository
from config import PINK, PURPLE

dash.register_page(__name__, path="/search", name="Ricerca Avanzata")

FILTER_FIELDS = [
    ("Codice paziente",     "code",            "text"),
    ("Età minima",          "age_min",         "number"),
    ("Età massima",         "age_max",         "number"),
    ("BMI minimo",          "bmi_min",         "number"),
    ("BMI massimo",         "bmi_max",         "number"),
    ("Tumore min (mm)",     "tumor_min",       "number"),
    ("Tumore max (mm)",     "tumor_max",       "number"),
    ("Grado",               "grade",           "select", ["","1","2","3"]),
    ("ER",                  "er_status",       "select", ["","Positivo","Negativo"]),
    ("PR",                  "pr_status",       "select", ["","Positivo","Negativo"]),
    ("HER2",                "her2_status",     "select", ["","Positivo","Negativo"]),
    ("Multifocalità",       "multifocality",   "select", ["","Sì","No"]),
    ("Linfonodi pos.",      "lymph_node",      "select", ["","Sì","No"]),
    ("Predizione AI",       "prediction",      "select", ["","BCS","Mastectomy"]),
    ("Chirurgia effettiva", "actual_surgery",  "select", ["","BCS","Mastectomy","Non eseguita"]),
    ("Ki67 max (%)",        "ki67_max",        "number"),
    ("Score alim. min",     "eating_min",      "number"),
]

def _input(label, key, typ, opts=None):
    lbl = dbc.Label(label, className="form-label")
    if typ == "select":
        w = dbc.Select(id=f"sf-{key}",
                       options=[{"label":o,"value":o} for o in opts],
                       value="")
    else:
        w = dbc.Input(id=f"sf-{key}", type=typ, placeholder="—")
    return dbc.Col([lbl, w], md=3, style={"marginBottom":"12px"})

layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Ricerca Avanzata", className="page-title"),
            html.P("Filtra pazienti su tutti i campi clinici simultaneamente",
                   className="page-subtitle"),
        ]),
        html.Div(id="search-count",
                 style={"fontWeight":"700","fontSize":"14px","color":PINK}),
    ], className="page-topbar"),

    html.Div([
        # Pannello filtri
        html.Div([
            html.Div([
                html.Div("🔍  Filtri di ricerca", className="card-title"),
                dbc.Row([_input(label,key,typ,opts if len(f)>3 else None)
                         for f in FILTER_FIELDS
                         for label,key,typ,*opts in [f]],
                        style={"rowGap":"4px"}),
                html.Div([
                    dbc.Button("🔍  Cerca", id="btn-search", className="btn-pink"),
                    dbc.Button("✕  Reset", id="btn-reset", className="btn-outline-purple",
                               style={"marginLeft":"10px"}),
                ], style={"marginTop":"8px"}),
            ], className="card-box mb-3"),
        ]),

        # Risultati
        html.Div(id="search-results"),
    ], style={"padding":"20px 24px"}),
])


@callback(
    Output("search-results","children"),
    Output("search-count","children"),
    Input("btn-search","n_clicks"),
    Input("btn-reset","n_clicks"),
    State("sf-code","value"),
    State("sf-age_min","value"),   State("sf-age_max","value"),
    State("sf-bmi_min","value"),   State("sf-bmi_max","value"),
    State("sf-tumor_min","value"), State("sf-tumor_max","value"),
    State("sf-grade","value"),
    State("sf-er_status","value"), State("sf-pr_status","value"),
    State("sf-her2_status","value"),
    State("sf-multifocality","value"), State("sf-lymph_node","value"),
    State("sf-prediction","value"), State("sf-actual_surgery","value"),
    State("sf-ki67_max","value"),  State("sf-eating_min","value"),
    prevent_initial_call=False,
)
def search(n_search, n_reset, code, age_min, age_max, bmi_min, bmi_max,
           tumor_min, tumor_max, grade, er, pr, her2,
           multi, lymph, pred, surgery, ki67_max, eating_min):

    rows = PatientRepository.get_all(search=code or "")

    def flt(row, key, val, op="eq"):
        rv = row.get(key)
        if rv is None or val is None or val == "": return True
        if op == "ge":  return float(rv) >= float(val)
        if op == "le":  return float(rv) <= float(val)
        if op == "eq":  return str(rv) == str(val)
        if op == "bool":return bool(rv) == (val == "Sì")
        return True

    def apply(rows):
        out = []
        for r in rows:
            if not flt(r,"age",age_min,"ge"):           continue
            if not flt(r,"age",age_max,"le"):           continue
            if not flt(r,"bmi",bmi_min,"ge"):           continue
            if not flt(r,"bmi",bmi_max,"le"):           continue
            if not flt(r,"tumor_size_mm",tumor_min,"ge"): continue
            if not flt(r,"tumor_size_mm",tumor_max,"le"): continue
            if grade and str(r.get("grade","")) != grade: continue
            if er and flt(r,"er_status",er,"bool") is False: continue
            if er:
                expected = er == "Positivo"
                if bool(r.get("er_status")) != expected: continue
            if pr:
                expected = pr == "Positivo"
                if bool(r.get("pr_status")) != expected: continue
            if her2:
                expected = her2 == "Positivo"
                if bool(r.get("her2_status")) != expected: continue
            if multi:
                expected = multi == "Sì"
                if bool(r.get("multifocality")) != expected: continue
            if lymph:
                expected = lymph == "Sì"
                if bool(r.get("lymph_node_positive")) != expected: continue
            if pred and r.get("last_prediction") != pred: continue
            if surgery and r.get("actual_surgery","") != surgery: continue
            if ki67_max and r.get("ki67_percent") is not None:
                if float(r["ki67_percent"]) > float(ki67_max): continue
            if eating_min and r.get("eating_habit_score") is not None:
                if float(r["eating_habit_score"]) < float(eating_min): continue
            out.append(r)
        return out

    filtered = apply(rows)

    if not filtered:
        return (html.Div([
            html.Div("🔎", style={"fontSize":"40px","textAlign":"center","marginBottom":"10px"}),
            html.Div("Nessun paziente corrisponde ai filtri.",
                     style={"textAlign":"center","color":"#6B7280","fontSize":"15px"}),
        ], style={"padding":"60px 0"}),
        f"0 pazienti trovati")

    for r in filtered:
        r["er_display"]   = "＋" if r.get("er_status")   else "－"
        r["pr_display"]   = "＋" if r.get("pr_status")   else "－"
        r["her2_display"] = "＋" if r.get("her2_status") else "－"
        r["multi_display"]= "Sì" if r.get("multifocality") else "No"
        r["lymph_display"]= "Sì" if r.get("lymph_node_positive") else "No"
        r.setdefault("last_prediction","—")

    table = dash_table.DataTable(
        data=filtered,
        columns=[
            {"name":"Codice",      "id":"code"},
            {"name":"Età",         "id":"age"},
            {"name":"BMI",         "id":"bmi"},
            {"name":"Tumore mm",   "id":"tumor_size_mm"},
            {"name":"Grado",       "id":"grade"},
            {"name":"ER",          "id":"er_display"},
            {"name":"PR",          "id":"pr_display"},
            {"name":"HER2",        "id":"her2_display"},
            {"name":"Ki67%",       "id":"ki67_percent"},
            {"name":"Multifoc.",   "id":"multi_display"},
            {"name":"Linfonodi",   "id":"lymph_display"},
            {"name":"Pred. AI",    "id":"last_prediction"},
            {"name":"Chirurgia",   "id":"actual_surgery"},
            {"name":"Score alim.", "id":"eating_habit_score"},
            {"name":"Attività fis.","id":"physical_activity"},
            {"name":"Aggiunto",    "id":"created_at"},
        ],
        sort_action="native",
        filter_action="native",
        page_size=25,
        style_table={"borderRadius":"12px","overflow":"hidden","border":"1px solid #E5E7EB"},
        style_cell={"textAlign":"left","padding":"10px 13px","fontSize":"12px",
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
            {"if":{"state":"selected"},"backgroundColor":"#FDF2F8","border":"none"},
        ],
        style_as_list_view=True,
        export_format="csv",
    )

    return table, f"{len(filtered)} pazienti trovati"


@callback(
    *[Output(f"sf-{key}","value") for _,key,*_ in FILTER_FIELDS],
    Input("btn-reset","n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    return [""] * len(FILTER_FIELDS)
