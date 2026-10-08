import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from database.db import PatientRepository
from ml.weka_bridge import FEATURES
from config import PINK

dash.register_page(__name__, path="/search", name="Ricerca Avanzata")

SI_NO = ["si", "no"]
# (id, etichetta, campo DB, tipo, opzioni, colonne)  — tipi: multi | select | text | range
FILTERS = {
    "📊  Vital Statistics": [
        ("sf-age", "Fascia età", "age_range", "multi", list(FEATURES["età"]), 4),
        ("sf-gender", "Sesso", "gender", "select", ["F", "M"], 2),
        ("sf-naz", "Nazionalità", "nazionalita", "text", None, 3),
        ("sf-blood", "Gruppo sang.", "blood_type", "multi", ["A", "B", "AB", "0"], 3),
    ],
    "📋  Clinical History": [
        ("sf-fumo", "Fumo", "fumo", "select", SI_NO, 3),
        ("sf-alcohol", "Alcool", "alcohol", "select", SI_NO, 3),
        ("sf-grav", "Gravidanza", "gravidanza", "select", SI_NO, 3),
        ("sf-diab", "Diabete", "diabetes", "select", SI_NO, 3),
        ("sf-brca", "Mutazione BRCA", "brca_mutation", "select", SI_NO, 3),
        ("sf-famov", "Fam. K.ovaio", "familiarita_carcinoma_ovarico", "select", SI_NO, 3),
        ("sf-prevbc", "K.mammella prec.", "previous_breast_cancer", "select", SI_NO, 3),
        ("sf-fambc", "Fam. K.mammella", "familial_breast_cancer", "select", SI_NO, 3),
        ("sf-tumor", "Dimensione tumore (mm)", "tumor_size_mm", "range", (0, 150), 6),
        ("sf-ki67", "Ki-67 (%)", "ki67", "range", (0, 100), 6),
    ],
    "🔬  Feature del modello (15)": [
        ("sf-strutt", "Struttura ghiandolare", "struttura_ghiandolare", "multi", FEATURES["struttura_ghiandolare"], 6),
        ("sf-cutedx", "Cute DX", "rapporto_cuteDX", "multi", FEATURES["rapporto_cuteDX"], 6),
        ("sf-cutesx", "Cute SX", "rapporto_cuteSX", "multi", FEATURES["rapporto_cuteSX"], 6),
        ("sf-aredx", "Areola-capezzolo DX", "rapporto_areola_capezzoloDX", "multi",
         FEATURES["rapporto_areola_capezzoloDX"], 6),
        ("sf-aresx", "Areola-capezzolo SX", "rapporto_areola_capezzoloSX", "multi",
         FEATURES["rapporto_areola_capezzoloSX"], 6),
        ("sf-lnfdx", "Linfonodi DX", "stato_linfonodaleDX", "multi", FEATURES["stato_linfonodaleDX"], 6),
        ("sf-lnfsx", "Linfonodi SX", "stato_linfonodaleSX", "multi", FEATURES["stato_linfonodaleSX"], 6),
        ("sf-birads", "BI-RADS clinico", "biRadsClinico", "multi", FEATURES["biRadsClinico"], 6),
        ("sf-cito", "Citologia", "citologia_codifica", "multi", FEATURES["citologia_codifica"], 4),
        ("sf-focal", "Focalità", "focalita", "select", FEATURES["focalità"], 4),
        ("sf-ricost", "Ricostruzione", "ricostruzione", "select", SI_NO, 4),
    ],
    "🎗  Outcome & Staging": [
        ("sf-pred", "Classificazione AI", "last_prediction", "select", ["CONSERVATIVA", "MASTECTOMIA"], 4),
        ("sf-disease", "DISEASE (effettivo)", "DISEASE", "select", ["CONSERVATIVA", "MASTECTOMIA"], 4),
        ("sf-grading", "Grading", "grading", "multi", ["G1", "G2", "G3"], 4),
        ("sf-stage", "Stadio clinico", "clinical_stage", "multi", ["I", "IIA", "IIB", "IIIA", "IIIB", "IIIC"], 4),
        ("sf-er", "ER", "er_status", "select", ["Positivo", "Negativo", "Borderline"], 4),
        ("sf-cerbb2", "CerbB2", "cerbb2", "select", ["Positivo", "Negativo", "Equivoco"], 4),
    ],
}
ALL = [f for group in FILTERS.values() for f in group]


def _default(ftype, opts):
    return [] if ftype == "multi" else (list(opts) if ftype == "range" else "")


def _widget(fid, label, _field, ftype, opts, md):
    if ftype == "multi":
        w = dcc.Dropdown(id=fid, options=opts, multi=True, placeholder="Tutti", style={"fontSize": "12px"})
    elif ftype == "select":
        w = dbc.Select(id=fid, value="", options=[{"label": "Tutti", "value": ""}] +
                       [{"label": o, "value": o} for o in opts], style={"fontSize": "12px", "height": "36px"})
    elif ftype == "range":
        w = dcc.RangeSlider(id=fid, min=opts[0], max=opts[1], step=1, value=list(opts), marks=None,
                            tooltip={"placement": "bottom", "always_visible": True})
    else:
        w = dbc.Input(id=fid, type="text", placeholder="contiene…", style={"height": "36px", "fontSize": "12px"})
    return dbc.Col([dbc.Label(label, className="form-label"), w], md=md, style={"marginBottom": "12px"})


layout = html.Div([
    html.Div([
        html.Div([html.H1("Ricerca Avanzata", className="page-title"),
                  html.P("Filtri su dati clinici e feature del modello", className="page-subtitle")]),
        html.Div(id="search-count", style={"fontWeight": "700", "fontSize": "14px", "color": PINK}),
    ], className="page-topbar"),
    html.Div([
        html.Div([
            html.Span("Combina i filtri attivi con: ", style={"fontSize": "13px", "fontWeight": "600"}),
            dbc.RadioItems(id="search-logic", value="and", inline=True,
                           options=[{"label": "AND — tutti veri", "value": "and"},
                                    {"label": "OR — almeno uno vero", "value": "or"}],
                           style={"marginLeft": "10px", "fontSize": "13px"}),
        ], style={"background": "#F4F6F9", "borderRadius": "10px", "padding": "10px 18px",
                  "marginBottom": "14px", "display": "flex", "alignItems": "center"}),
        # Tutti i widget sono SEMPRE nel DOM (Accordion), così i State() hanno sempre un valore
        dbc.Accordion([dbc.AccordionItem(dbc.Row([_widget(*f) for f in group]), title=title)
                       for title, group in FILTERS.items()],
                      start_collapsed=True, always_open=True, style={"marginBottom": "14px"}),
        html.Div([dbc.Button("🔍  Cerca", id="btn-search", className="btn-pink"),
                  dbc.Button("✕  Reset", id="btn-reset", className="btn-outline-purple",
                             style={"marginLeft": "10px"})], style={"marginBottom": "16px"}),
        html.Div(id="search-results"),
    ], style={"padding": "20px 24px"}),
])


def _match(row, field, ftype, val, opts):
    v = row.get(field)
    if ftype == "multi":
        return str(v) in val
    if ftype == "select":
        return str(v) == str(val)
    if ftype == "text":
        return str(val).lower() in str(v or "").lower()
    if v is None:
        return False
    try:
        return float(val[0]) <= float(v) <= float(val[1])
    except (TypeError, ValueError):
        return False


def _is_active(ftype, val, opts):
    if ftype == "range":
        return bool(val) and list(val) != list(opts)
    return bool(val)


@callback(
    Output("search-results", "children"), Output("search-count", "children"),
    Input("btn-search", "n_clicks"), State("search-logic", "value"),
    *[State(f[0], "value") for f in ALL],
    prevent_initial_call=True,
)
def do_search(_n, logic, *values):
    active = [(f, v) for f, v in zip(ALL, values) if _is_active(f[3], v, f[4])]
    rows = PatientRepository.get_all()
    if active:
        test = all if logic == "and" else any
        rows = [r for r in rows if test(_match(r, f[2], f[3], v, f[4]) for f, v in active)]
    if not rows:
        return (html.Div("🔎  Nessun paziente corrisponde ai filtri.",
                         style={"textAlign": "center", "color": "#6B7280", "padding": "40px 0"}), "0 pazienti")
    for r in rows:
        r["last_prediction"] = r.get("last_prediction") or "—"
        r["DISEASE"] = r.get("DISEASE") or "—"
    table = dash_table.DataTable(
        data=rows, columns=[{"name": n, "id": k} for n, k in [
            ("Codice", "code"), ("Età", "age_range"), ("BI-RADS", "biRadsClinico"), ("Focalità", "focalita"),
            ("Linfon. DX", "stato_linfonodaleDX"), ("Citologia", "citologia_codifica"),
            ("Tumore mm", "tumor_size_mm"), ("Grading", "grading"), ("Pred. AI", "last_prediction"),
            ("DISEASE", "DISEASE")]],
        sort_action="native", filter_action="native", page_size=25, export_format="csv",
        style_table={"borderRadius": "12px", "overflow": "hidden", "border": "1px solid #E5E7EB"},
        style_cell={"textAlign": "left", "padding": "10px 13px", "fontSize": "12px",
                    "fontFamily": "Inter,Arial,sans-serif", "border": "none", "borderBottom": "1px solid #F3F4F6"},
        style_header={"backgroundColor": "#EDE7F6", "color": "#4A235A", "fontWeight": "700", "fontSize": "11px",
                      "textTransform": "uppercase", "border": "none"},
        style_data_conditional=[
            {"if": {"filter_query": "{last_prediction} = 'CONSERVATIVA'", "column_id": "last_prediction"},
             "color": "#059669", "fontWeight": "700"},
            {"if": {"filter_query": "{last_prediction} = 'MASTECTOMIA'", "column_id": "last_prediction"},
             "color": "#DC2626", "fontWeight": "700"}],
        style_as_list_view=True)
    label = f"{len(rows)} pazienti" + (f" · {len(active)} filtri in {logic.upper()}" if active else " · nessun filtro")
    return table, label


@callback(*[Output(f[0], "value") for f in ALL], Input("btn-reset", "n_clicks"), prevent_initial_call=True)
def reset(_n):
    return [_default(f[3], f[4]) for f in ALL]
