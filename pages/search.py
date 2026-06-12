import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from ml.weka_bridge import FEATURES, FEATURE_LABELS
from config import PINK, PURPLE

dash.register_page(__name__, path="/search", name="Ricerca Avanzata")

# ── Filtri per sezione ────────────────────────────────────────────────────────
VITAL_FILTERS = [
    ("Fascia età",    "age_range",   "multi",  None, list(FEATURES["età"])),
    ("Sesso",         "gender",      "select", None, ["F","M"]),
    ("Nazionalità",   "nazionalita", "text",   None, None),
    ("Gruppo sang.",  "blood_type",  "multi",  None, ["A","B","AB","0"]),
]

CLINICAL_FILTERS = [
    ("Fumo",           "fumo",          "select", None, ["si","no"]),
    ("Gravidanza",     "gravidanza",    "select", None, ["si","no"]),
    ("Alcool",         "alcohol",       "select", None, ["si","no"]),
    ("Mutazione BRCA", "brca_mutation", "select", None, ["si","no"]),
    ("Familiarità K.ovaio","familiarita_carcinoma_ovarico","select",None,["si","no"]),
    ("Diabete",        "diabetes",      "select", None, ["si","no"]),
    ("K. mammella prec.","previous_breast_cancer","select",None,["si","no"]),
    ("Dimensione tumore (mm)","tumor_size_mm","range",None,None),
    ("Ki-67 (%)","ki67","range",None,None),
]

MODEL_FILTERS = [
    ("Struttura ghiandolare","struttura_ghiandolare","multi",None,FEATURES["struttura_ghiandolare"]),
    ("Cute DX",              "rapporto_cuteDX",      "multi",None,FEATURES["rapporto_cuteDX"]),
    ("Cute SX",              "rapporto_cuteSX",      "multi",None,FEATURES["rapporto_cuteSX"]),
    ("Areola-capezzolo DX",  "rapporto_areola_capezzoloDX","multi",None,FEATURES["rapporto_areola_capezzoloDX"]),
    ("Areola-capezzolo SX",  "rapporto_areola_capezzoloSX","multi",None,FEATURES["rapporto_areola_capezzoloSX"]),
    ("Stato linfonodale DX", "stato_linfonodaleDX",  "multi",None,FEATURES["stato_linfonodaleDX"]),
    ("Stato linfonodale SX", "stato_linfonodaleSX",  "multi",None,FEATURES["stato_linfonodaleSX"]),
    ("BI-RADS clinico",      "biRadsClinico",        "multi",None,FEATURES["biRadsClinico"]),
    ("Citologia",            "citologia_codifica",   "select",None,["si","no"]),
    ("Focalità",             "focalita",             "select",None,["si","no"]),
    ("Ricostruzione",        "ricostruzione",        "select",None,["si","no"]),
]

OUTCOME_FILTERS = [
    ("Classificazione AI","last_prediction","select",None,["CONSERVATIVA","MASTECTOMIA"]),
    ("DISEASE (effettivo)","DISEASE","select",None,["CONSERVATIVA","MASTECTOMIA"]),
    ("Grading","grading","multi",None,["G1","G2","G3"]),
    ("Stadio clinico","clinical_stage","multi",None,["I","IIA","IIB","IIIA","IIIB","IIIC"]),
    ("ER","er_status","select",None,["Positivo","Negativo","Borderline"]),
    ("PgR","pgr_status","select",None,["Positivo","Negativo","Borderline"]),
    ("CerbB2","cerbb2","select",None,["Positivo","Negativo","Equivoco"]),
]

ALL_SECTIONS = [
    ("📊  Vital Statistics",        VITAL_FILTERS),
    ("📋  Clinical History",        CLINICAL_FILTERS),
    ("🔬  Feature Modello",         MODEL_FILTERS),
    ("🎗  Outcome & Staging",       OUTCOME_FILTERS),
]

def _filter_widget(label, key, ftype, _, opts):
    fid = f"sf-{key}"
    lbl = dbc.Label(label, className="form-label", style={"fontSize":"12px"})
    if ftype == "multi":
        w = dcc.Dropdown(id=fid, options=[{"label":o,"value":o} for o in (opts or [])],
                         multi=True, placeholder=f"Tutti", style={"fontSize":"12px"})
    elif ftype == "select":
        w = dbc.Select(id=fid, options=[{"label":"Tutti","value":""}]
                       +[{"label":o,"value":o} for o in (opts or [])], value="",
                       style={"fontSize":"12px","height":"36px"})
    elif ftype == "range":
        w = html.Div([
            dcc.RangeSlider(id=fid, min=0, max=200 if "tumore" in label else 100,
                            step=1, value=[0, 200 if "tumore" in label else 100],
                            marks=None,
                            tooltip={"placement":"bottom","always_visible":True}),
        ], style={"padding":"4px 0"})
    else:
        w = dbc.Input(id=fid, type="text", placeholder="—",
                      style={"height":"36px","fontSize":"12px"})
    return dbc.Col([lbl, w], md=4, style={"marginBottom":"14px"})


layout = html.Div([
    html.Div([
        html.Div([html.H1("Ricerca Avanzata",className="page-title"),
                  html.P("Filtra su tutti i campi clinici e del modello",className="page-subtitle")]),
        html.Div(id="search-count",
                 style={"fontWeight":"700","fontSize":"14px","color":PINK}),
    ], className="page-topbar"),

    html.Div([
        # Logica AND/OR
        html.Div([
            html.Span("Logica di ricerca: ", style={"fontSize":"13px","fontWeight":"600","color":"#374151"}),
            dbc.RadioItems(id="search-logic",
                options=[{"label":"AND  (tutti i filtri)","value":"and"},
                         {"label":"OR  (almeno un filtro)","value":"or"}],
                value="and", inline=True,
                style={"display":"inline-block","marginLeft":"12px","fontSize":"13px"}),
        ], style={"background":"#F4F6F9","borderRadius":"10px","padding":"12px 18px",
                  "marginBottom":"16px","display":"flex","alignItems":"center"}),

        # Sezioni filtri in tab
        dbc.Tabs([
            dbc.Tab(label=sec_title, tab_id=f"sec-{i}",
                    label_style={"fontWeight":"600","fontSize":"12px"})
            for i, (sec_title, _) in enumerate(ALL_SECTIONS)
        ], id="search-tabs", active_tab="sec-0", style={"marginBottom":"16px"}),

        html.Div(id="search-filter-panel"),

        html.Div([
            dbc.Button("🔍  Cerca",  id="btn-search",  className="btn-pink"),
            dbc.Button("✕  Reset",  id="btn-reset",   className="btn-outline-purple",
                       style={"marginLeft":"10px"}),
            dbc.Button("📥  Esporta CSV", id="btn-export-search", color="light",
                       style={"marginLeft":"10px","borderRadius":"8px"}),
        ], style={"marginBottom":"16px"}),

        html.Div(id="search-results"),
    ], style={"padding":"20px 24px"}),

    dcc.Store(id="search-data-store"),
])

# Genera ID unici per tutti i filtri
ALL_FILTER_IDS = []
for _, flist in ALL_SECTIONS:
    for label, key, ftype, *_ in flist:
        ALL_FILTER_IDS.append((key, ftype))


@callback(Output("search-filter-panel","children"),
          Input("search-tabs","active_tab"))
def show_filters(tab):
    idx = int(tab.split("-")[1])
    _, flist = ALL_SECTIONS[idx]
    return dbc.Row([_filter_widget(*f) for f in flist])


@callback(
    Output("search-results","children"),
    Output("search-count","children"),
    Input("btn-search","n_clicks"),
    State("search-logic","value"),
    # Vital
    State("sf-age_range","value"),State("sf-gender","value"),
    State("sf-nazionalita","value"),State("sf-blood_type","value"),
    # Clinical
    State("sf-fumo","value"),State("sf-gravidanza","value"),
    State("sf-alcohol","value"),State("sf-brca_mutation","value"),
    State("sf-familiarita_carcinoma_ovarico","value"),
    State("sf-diabetes","value"),State("sf-previous_breast_cancer","value"),
    State("sf-tumor_size_mm","value"),State("sf-ki67","value"),
    # Model
    State("sf-struttura_ghiandolare","value"),
    State("sf-rapporto_cuteDX","value"),State("sf-rapporto_cuteSX","value"),
    State("sf-rapporto_areola_capezzoloDX","value"),State("sf-rapporto_areola_capezzoloSX","value"),
    State("sf-stato_linfonodaleDX","value"),State("sf-stato_linfonodaleSX","value"),
    State("sf-biRadsClinico","value"),State("sf-citologia_codifica","value"),
    State("sf-focalita","value"),State("sf-ricostruzione","value"),
    # Outcome
    State("sf-last_prediction","value"),State("sf-DISEASE","value"),
    State("sf-grading","value"),State("sf-clinical_stage","value"),
    State("sf-er_status","value"),State("sf-pgr_status","value"),State("sf-cerbb2","value"),
    prevent_initial_call=True,
)
def search(n, logic,
           age_range, gender, nazionalita, blood_type,
           fumo, gravidanza, alcohol, brca, fam_ovaio, diabete, prev_bc,
           tumor_range, ki67_range,
           struttura, cute_dx, cute_sx, areola_dx, areola_sx,
           linfo_dx, linfo_sx, birads, citologia, focalita, ricost,
           pred, disease, grading, stage, er, pgr, cerbb2):

    rows = PatientRepository.get_all()

    def passes(r):
        checks = []
        def chk_select(val, field):
            if not val: return True
            return str(r.get(field,"")) == str(val)
        def chk_multi(val, field):
            if not val: return True
            return str(r.get(field,"")) in val
        def chk_range(val, field):
            if not val: return True
            lo, hi = val
            v = r.get(field)
            if v is None: return True
            try: return lo <= float(v) <= hi
            except: return True
        def chk_text(val, field):
            if not val: return True
            return val.lower() in str(r.get(field,"")).lower()

        checks += [
            chk_multi(age_range,"age_range"), chk_select(gender,"gender"),
            chk_text(nazionalita,"nazionalita"), chk_multi(blood_type,"blood_type"),
            chk_select(fumo,"fumo"), chk_select(gravidanza,"gravidanza"),
            chk_select(alcohol,"alcohol"), chk_select(brca,"brca_mutation"),
            chk_select(fam_ovaio,"familiarita_carcinoma_ovarico"),
            chk_select(diabete,"diabetes"), chk_select(prev_bc,"previous_breast_cancer"),
            chk_range(tumor_range,"tumor_size_mm"), chk_range(ki67_range,"ki67"),
            chk_multi(struttura,"struttura_ghiandolare"),
            chk_multi(cute_dx,"rapporto_cuteDX"), chk_multi(cute_sx,"rapporto_cuteSX"),
            chk_multi(areola_dx,"rapporto_areola_capezzoloDX"),
            chk_multi(areola_sx,"rapporto_areola_capezzoloSX"),
            chk_multi(linfo_dx,"stato_linfonodaleDX"),
            chk_multi(linfo_sx,"stato_linfonodaleSX"),
            chk_multi(birads,"biRadsClinico"),
            chk_select(citologia,"citologia_codifica"),
            chk_select(focalita,"focalita"), chk_select(ricost,"ricostruzione"),
            chk_select(pred,"last_prediction"), chk_select(disease,"DISEASE"),
            chk_multi(grading,"grading"), chk_multi(stage,"clinical_stage"),
            chk_select(er,"er_status"), chk_select(pgr,"pgr_status"),
            chk_select(cerbb2,"cerbb2"),
        ]
        # Rimuovi True triviali (filtri non attivi)
        active = [c for c in checks]
        if logic == "and":
            return all(active)
        else:
            non_trivial = [c for c, (k,ft) in zip(active,ALL_FILTER_IDS)
                           if _filter_active(k,ft,locals())]
            return any(non_trivial) if non_trivial else True

    filtered = [r for r in rows if passes(r)]

    if not filtered:
        return (html.Div([
            html.Div("🔎",style={"fontSize":"36px","textAlign":"center","marginBottom":"8px"}),
            html.Div("Nessun paziente corrisponde ai filtri.",
                     style={"textAlign":"center","color":"#6B7280","fontSize":"15px"}),
        ],style={"padding":"50px 0"}), "0 pazienti")

    for r in filtered:
        r.setdefault("last_prediction","—")
        r.setdefault("DISEASE","—")

    table = dash_table.DataTable(
        data=filtered,
        columns=[
            {"name":"Codice",    "id":"code"},
            {"name":"Età",       "id":"age_range"},
            {"name":"Sesso",     "id":"gender"},
            {"name":"BI-RADS",   "id":"biRadsClinico"},
            {"name":"Focalità",  "id":"focalita"},
            {"name":"Linfon. DX","id":"stato_linfonodaleDX"},
            {"name":"Citologia", "id":"citologia_codifica"},
            {"name":"Pred. AI",  "id":"last_prediction"},
            {"name":"DISEASE",   "id":"DISEASE"},
            {"name":"Tumore mm", "id":"tumor_size_mm"},
            {"name":"Grading",   "id":"grading"},
            {"name":"Stadio",    "id":"clinical_stage"},
        ],
        sort_action="native", filter_action="native",
        page_size=30, export_format="csv",
        style_table={"borderRadius":"12px","overflow":"hidden","border":"1px solid #E5E7EB"},
        style_cell={"textAlign":"left","padding":"10px 13px","fontSize":"12px",
                    "fontFamily":"Inter,Arial,sans-serif","border":"none",
                    "borderBottom":"1px solid #F3F4F6"},
        style_header={"backgroundColor":"#EDE7F6","color":"#4A235A","fontWeight":"700",
                      "fontSize":"11px","textTransform":"uppercase","letterSpacing":"0.5px",
                      "border":"none","borderBottom":"1px solid #E5E7EB"},
        style_data_conditional=[
            {"if":{"filter_query":"{last_prediction} = 'CONSERVATIVA'","column_id":"last_prediction"},
             "color":"#059669","fontWeight":"700"},
            {"if":{"filter_query":"{last_prediction} = 'MASTECTOMIA'","column_id":"last_prediction"},
             "color":"#DC2626","fontWeight":"700"},
        ],
        style_as_list_view=True,
    )
    return table, f"{len(filtered)} pazienti trovati (logica: {logic.upper()})"


def _filter_active(key, ftype, loc):
    v = loc.get(f"sf_{key}")
    if v is None or v == "" or v == []: return False
    return True


# Reset
@callback(
    Output("sf-age_range","value"), Output("sf-gender","value"),
    Output("sf-nazionalita","value"), Output("sf-blood_type","value"),
    Output("sf-fumo","value"), Output("sf-gravidanza","value"),
    Output("sf-alcohol","value"), Output("sf-brca_mutation","value"),
    Output("sf-familiarita_carcinoma_ovarico","value"),
    Output("sf-diabetes","value"), Output("sf-previous_breast_cancer","value"),
    Output("sf-tumor_size_mm","value"), Output("sf-ki67","value"),
    Output("sf-struttura_ghiandolare","value"),
    Output("sf-rapporto_cuteDX","value"), Output("sf-rapporto_cuteSX","value"),
    Output("sf-rapporto_areola_capezzoloDX","value"),Output("sf-rapporto_areola_capezzoloSX","value"),
    Output("sf-stato_linfonodaleDX","value"),Output("sf-stato_linfonodaleSX","value"),
    Output("sf-biRadsClinico","value"),Output("sf-citologia_codifica","value"),
    Output("sf-focalita","value"),Output("sf-ricostruzione","value"),
    Output("sf-last_prediction","value"),Output("sf-DISEASE","value"),
    Output("sf-grading","value"),Output("sf-clinical_stage","value"),
    Output("sf-er_status","value"),Output("sf-pgr_status","value"),Output("sf-cerbb2","value"),
    Input("btn-reset","n_clicks"),
    prevent_initial_call=True,
)
def reset_all(_):
    return ([],[],"",[],
            "","","","","","","",
            [0,200],[0,100],
            [],[],[],[],[],[],[],[],
            "","","",
            "","","","","","","")
