import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database.db import PatientRepository, ClassificationRepository
from ml.weka_bridge import (run_classification, FEATURE_NAMES,
                             FEATURE_LABELS, FEATURE_GROUPS)
from config import PINK, PURPLE

def _conf_row(label, key, color):
    return html.Div([
        html.Div([
            html.Span(label, style={"fontSize":"13px","minWidth":"90px"}),
            dbc.Progress(id=f"bar-{key}", value=0,
                         color="success" if key=="bcs" else "danger",
                         style={"flex":"1","height":"14px","borderRadius":"6px"}),
            html.Span("—%", id=f"pct-{key}",
                      style={"minWidth":"48px","textAlign":"right",
                             "fontWeight":"700","color":color,"fontSize":"13px"}),
        ], style={"display":"flex","alignItems":"center",
                  "gap":"10px","marginBottom":"8px"}),
    ])

dash.register_page(__name__, path="/classification", name="Classificazione")

# Input type per feature (0/1 = select, altrimenti number)
BINARY = {"fumo","gravidanza","allattamento","menopausa",
          "casi_vero_famiglia","familiarita_carcinoma_ovario",
          "intervento_chirurgico_bilaterale","ricostruzione"}

def _input(feat):
    label = FEATURE_LABELS.get(feat, feat)
    if feat in BINARY:
        return dbc.Col([
            dbc.Label(label, className="form-label", style={"fontSize":"12px"}),
            dbc.Select(id=f"feat-{feat}",
                       options=[{"label":"—","value":""},
                                {"label":"No (0)","value":"0"},
                                {"label":"Sì (1)","value":"1"}],
                       value=""),
        ], md=4, style={"marginBottom":"10px"})
    return dbc.Col([
        dbc.Label(label, className="form-label", style={"fontSize":"12px"}),
        dbc.Input(id=f"feat-{feat}", type="number", step=0.01,
                  placeholder="—", style={"height":"36px","fontSize":"13px"}),
    ], md=4, style={"marginBottom":"10px"})


layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Classificazione AI", className="page-title"),
            html.P("Predizione chirurgica — modello BrCaM (Lucasilvestri et al.)",
                   className="page-subtitle"),
        ]),
    ], className="page-topbar"),

    html.Div([
        dbc.Row([
            # ── Sinistra: form ────────────────────────────────────────────────
            dbc.Col([
                # Selezione paziente
                html.Div([
                    html.Div("Seleziona paziente dal DB (opzionale)", className="card-title"),
                    html.P("Pre-compila i campi con i dati già inseriti.",
                           style={"fontSize":"12px","color":"#6B7280","marginBottom":"8px"}),
                    dcc.Dropdown(id="pt-select", placeholder="— Nuovo soggetto —",
                                 clearable=True, style={"fontSize":"13px"}),
                ], className="card-box mb-3"),

                # Input per gruppo
                *[html.Div([
                    html.Div(grp_title, className="form-section"),
                    dbc.Row([_input(f) for f in feats], style={"rowGap":"0px"}),
                ]) for grp_title, feats in FEATURE_GROUPS.items()],

                dbc.Label("Note clinico", className="form-label mt-3"),
                dbc.Textarea(id="clf-notes", rows=2,
                             style={"borderRadius":"7px","fontSize":"13px"}),
                dbc.Button(
                    [html.Span("🚀", style={"marginRight":"8px"}),
                     "Esegui classificazione"],
                    id="btn-classify", className="btn-pink w-100 mt-3",
                    style={"height":"50px","fontSize":"15px"},
                ),
                html.Div(id="clf-error",
                         style={"color":"#DC2626","fontSize":"13px","marginTop":"8px"}),

            ], md=7),

            # ── Destra: risultato + storico ───────────────────────────────────
            dbc.Col([
                # Result card
                html.Div([
                    html.Div("Risultato predizione",
                             style={"fontSize":"13px","fontWeight":"700",
                                    "color":"#6B7280","marginBottom":"12px"}),
                    html.Div("—", id="result-icon",
                             style={"fontSize":"48px","textAlign":"center"}),
                    html.Div("In attesa…", id="result-label",
                             style={"fontSize":"28px","fontWeight":"800",
                                    "color":"#D1D5DB","textAlign":"center","margin":"6px 0"}),
                    html.Div([
                        _conf_row("BCS",        "bcs",  "#059669"),
                        _conf_row("Mastectomy", "mast", "#DC2626"),
                    ], style={"marginTop":"16px"}),
                    html.Div("", id="result-model",
                             style={"fontSize":"11px","color":"#9CA3AF","marginTop":"10px","textAlign":"center"}),
                ], className="result-card mb-3"),

                html.Div("Classificazioni recenti",
                         style={"fontSize":"14px","fontWeight":"700",
                                "color":"#1A1A2E","marginBottom":"8px"}),
                html.Div(id="clf-history"),

            ], md=5),
        ], className="g-3"),
        dcc.Store(id="clf-store"),
    ], style={"padding":"20px 24px"}),
])




@callback(Output("pt-select","options"), Input("clf-store","data"))
def refresh_dropdown(_):
    pts = PatientRepository.get_all()
    return [{"label":p["code"],"value":p["id"]} for p in pts]


@callback(
    *[Output(f"feat-{f}","value") for f in FEATURE_NAMES],
    Input("pt-select","value"),
    prevent_initial_call=True,
)
def fill_from_patient(pid):
    empty = [""] * len(FEATURE_NAMES)
    if not pid: return empty
    pts = PatientRepository.get_all()
    p   = next((x for x in pts if x.get("id")==int(pid)), None)
    if not p: return empty
    return [p.get(f,"") or "" for f in FEATURE_NAMES]


@callback(
    Output("result-icon","children"),
    Output("result-label","children"),
    Output("result-label","style"),
    Output("bar-bcs","value"),   Output("pct-bcs","children"),
    Output("bar-mast","value"),  Output("pct-mast","children"),
    Output("result-model","children"),
    Output("clf-history","children"),
    Output("clf-error","children"),
    Output("clf-store","data"),
    Input("btn-classify","n_clicks"),
    State("pt-select","value"),
    *[State(f"feat-{f}","value") for f in FEATURE_NAMES],
    State("clf-notes","value"),
    prevent_initial_call=True,
)
def classify(n_clicks, pid, *args):
    feat_vals = args[:len(FEATURE_NAMES)]
    notes     = args[-1] or ""

    # Valida
    missing = []
    features = {}
    for f, v in zip(FEATURE_NAMES, feat_vals):
        if v is None or str(v).strip() == "":
            missing.append(FEATURE_LABELS.get(f,f))
        else:
            try: features[f] = float(v)
            except: missing.append(f)

    if missing:
        err = f"Campi mancanti: {', '.join(missing[:5])}{'…' if len(missing)>5 else ''}"
        return ("—","Dati incompleti",
                {"fontSize":"18px","fontWeight":"700","color":"#F59E0B","textAlign":"center"},
                0,"—%",0,"—%","",dash.no_update,err,dash.no_update)

    label, c_bcs, c_mast, ver = run_classification(features)

    if pid:
        from database.db import ClassificationRepository
        ClassificationRepository.save(
            patient_id=int(pid), predicted=label,
            conf_bcs=c_bcs, conf_mast=c_mast,
            model_ver=ver, input_snap=features, notes=notes)

    color = {"BCS":"#059669","Mastectomy":"#DC2626"}.get(label,"#6B7280")
    icon  = {"BCS":"✂️","Mastectomy":"🏥"}.get(label,"?")
    style = {"fontSize":"28px","fontWeight":"800","color":color,
             "textAlign":"center","margin":"6px 0"}

    return (icon, label, style,
            round(c_bcs*100,1), f"{c_bcs*100:.1f}%",
            round(c_mast*100,1),f"{c_mast*100:.1f}%",
            f"Modello: {ver}", _history(), "", str(n_clicks))


def _history():
    from database.db import ClassificationRepository
    results = ClassificationRepository.get_all()[:12]
    if not results:
        return html.P("Nessuna classificazione.", style={"color":"#6B7280","fontSize":"13px"})
    items = []
    for r in results:
        badge = "badge-bcs" if r["predicted_class"]=="BCS" else "badge-mast"
        items.append(html.Div([
            html.Span(r["patient_code"],
                      style={"fontWeight":"700","minWidth":"80px","fontSize":"13px"}),
            html.Span(r["predicted_class"], className=badge),
            html.Span(f"BCS {r['confidence_bcs']}%" if r.get("confidence_bcs") else "",
                      style={"color":"#6B7280","fontSize":"12px"}),
            html.Span(r["run_at"],
                      style={"marginLeft":"auto","color":"#9CA3AF","fontSize":"11px"}),
        ], className="hist-row"))
    return html.Div(items)
