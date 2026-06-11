import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database.db import ClassificationRepository, PatientRepository
from ml.weka_bridge import (run_classification, FEATURES, FEATURE_NAMES,
                             FEATURE_LABELS, FEATURE_GROUPS,
                             CLASS_DISPLAY, CLASS_COLOR)
from config import PINK, PURPLE

dash.register_page(__name__, path="/classification", name="Classificazione")


def _dropdown(feat):
    """Dropdown con i valori nominali esatti del modello."""
    values = FEATURES[feat]
    return dbc.Col([
        dbc.Label(FEATURE_LABELS.get(feat, feat),
                  className="form-label", style={"fontSize":"12px"}),
        dbc.Select(
            id=f"feat-{feat.replace('à','a').replace('è','e').replace('ì','i')}",
            options=[{"label":"— seleziona —","value":""}]
                   +[{"label":v,"value":v} for v in values],
            value="",
        ),
    ], md=6, style={"marginBottom":"10px"})


def _safe_id(feat):
    return feat.replace('à','a').replace('è','e').replace('ì','i').replace('ò','o').replace('ù','u')


def _conf_row(label, key, color):
    return html.Div([html.Div([
        html.Span(label, style={"fontSize":"13px","minWidth":"110px"}),
        dbc.Progress(id=f"bar-{key}", value=0,
                     color="success" if key=="cons" else "danger",
                     style={"flex":"1","height":"14px","borderRadius":"6px"}),
        html.Span("—%", id=f"pct-{key}",
                  style={"minWidth":"48px","textAlign":"right",
                         "fontWeight":"700","color":color,"fontSize":"13px"}),
    ], style={"display":"flex","alignItems":"center","gap":"10px","marginBottom":"8px"})])


layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Classificazione AI", className="page-title"),
            html.P(
                f"Modello BrCaM · {len(FEATURE_NAMES)} feature nominali · "
                f"Output: CONSERVATIVA / MASTECTOMIA",
                className="page-subtitle"),
        ]),
        html.Div(id="clf-model-badge"),
    ], className="page-topbar"),

    html.Div([
        dbc.Row([
            # ── Sinistra: form ────────────────────────────────────────────────
            dbc.Col([
                # Selezione paziente DB (opzionale)
                html.Div([
                    html.Div("Paziente dal database", className="card-title"),
                    html.P("Opzionale — pre-compila i campi se disponibili.",
                           style={"fontSize":"12px","color":"#6B7280","marginBottom":"8px"}),
                    dcc.Dropdown(id="pt-select", placeholder="— Nuovo soggetto —",
                                 clearable=True, style={"fontSize":"13px"}),
                ], className="card-box mb-3"),

                # Feature per gruppo — tutti dropdown
                *[html.Div([
                    html.Div(grp, className="form-section"),
                    dbc.Row([_dropdown(f) for f in feats]),
                ]) for grp, feats in FEATURE_GROUPS.items()],

                dbc.Label("Note clinico", className="form-label mt-2"),
                dbc.Textarea(id="clf-notes", rows=2,
                             style={"borderRadius":"7px","fontSize":"13px"}),

                dbc.Button(
                    "🚀   Esegui classificazione",
                    id="btn-classify", className="btn-pink w-100 mt-3",
                    style={"height":"50px","fontSize":"15px"},
                ),
                html.Div(id="clf-error",
                         style={"color":"#DC2626","fontSize":"13px","marginTop":"8px"}),
            ], md=7),

            # ── Destra: risultato ─────────────────────────────────────────────
            dbc.Col([
                html.Div([
                    html.Div("Risultato predizione",
                             style={"fontSize":"13px","fontWeight":"700",
                                    "color":"#6B7280","marginBottom":"12px"}),
                    html.Div("—", id="result-icon",
                             style={"fontSize":"48px","textAlign":"center"}),
                    html.Div("In attesa…", id="result-label",
                             style={"fontSize":"26px","fontWeight":"800",
                                    "color":"#D1D5DB","textAlign":"center","margin":"6px 0"}),
                    _conf_row("Conservativa","cons","#059669"),
                    _conf_row("Mastectomia", "mast","#DC2626"),
                    html.Div("", id="result-model",
                             style={"fontSize":"11px","color":"#9CA3AF",
                                    "marginTop":"10px","textAlign":"center"}),
                ], className="result-card mb-3"),

                html.Div("Classificazioni recenti",
                         style={"fontSize":"14px","fontWeight":"700",
                                "color":"#1A1A2E","marginBottom":"8px"}),
                html.Div(id="clf-history"),
            ], md=5),
        ], className="g-3"),
        dcc.Store(id="clf-store"),
        dcc.Interval(id="clf-init", interval=400, n_intervals=0, max_intervals=1),
    ], style={"padding":"20px 24px"}),
])


@callback(Output("clf-model-badge","children"), Input("clf-init","n_intervals"))
def show_badge(_):
    from ml.weka_bridge import get_model_info
    info  = get_model_info()
    active= info.get("active", False)
    color = "#059669" if active else "#F59E0B"
    label = ("✓  Modello WEKA originale attivo" if active
             else "⚠  Fallback scikit-learn attivo")
    return html.Span(label, style={"background":color+"22","color":color,
                                    "fontWeight":"700","fontSize":"12px",
                                    "padding":"6px 14px","borderRadius":"20px"})


@callback(Output("pt-select","options"),
          Input("clf-store","data"), Input("clf-init","n_intervals"))
def refresh_dd(_,__):
    return [{"label":p["code"],"value":p["id"]}
            for p in PatientRepository.get_all()]


# Pre-compila dal paziente (se i dati sono presenti nel DB)
@callback(
    *[Output(f"feat-{_safe_id(f)}","value") for f in FEATURE_NAMES],
    Input("pt-select","value"),
    prevent_initial_call=True,
)
def fill_patient(pid):
    empty = [""] * len(FEATURE_NAMES)
    if not pid: return empty
    pts = PatientRepository.get_all()
    p   = next((x for x in pts if x.get("id")==int(pid)), {})
    # Mappa: il DB potrebbe non avere queste feature nominali
    # restituisce "" se non presente
    return [str(p.get(f,"")) or "" for f in FEATURE_NAMES]


@callback(
    Output("result-icon","children"),
    Output("result-label","children"),
    Output("result-label","style"),
    Output("bar-cons","value"),   Output("pct-cons","children"),
    Output("bar-mast","value"),   Output("pct-mast","children"),
    Output("result-model","children"),
    Output("clf-history","children"),
    Output("clf-error","children"),
    Output("clf-store","data"),
    Input("btn-classify","n_clicks"),
    State("pt-select","value"),
    *[State(f"feat-{_safe_id(f)}","value") for f in FEATURE_NAMES],
    State("clf-notes","value"),
    prevent_initial_call=True,
)
def classify(n_clicks, pid, *args):
    feat_vals = args[:len(FEATURE_NAMES)]
    notes     = args[-1] or ""

    # Valida: tutti i campi devono essere selezionati
    missing  = [FEATURE_LABELS.get(f,f) for f,v in zip(FEATURE_NAMES,feat_vals)
                if not v or str(v).strip()==""]
    if missing:
        short = ", ".join(missing[:4]) + ("…" if len(missing)>4 else "")
        return ("⚠️","Dati incompleti",
                {"fontSize":"18px","fontWeight":"700","color":"#F59E0B","textAlign":"center"},
                0,"—%",0,"—%","",dash.no_update,
                f"Seleziona tutti i campi ({len(missing)} mancanti): {short}",dash.no_update)

    features = {f: v for f,v in zip(FEATURE_NAMES, feat_vals)}
    label, c_cons, c_mast, ver = run_classification(features)

    if pid:
        ClassificationRepository.save(
            patient_id=int(pid), predicted=label,
            conf_bcs=c_cons, conf_mast=c_mast,
            model_ver=ver, input_snap=features, notes=notes)

    display = CLASS_DISPLAY.get(label, label)
    color   = CLASS_COLOR.get(label, "#6B7280")
    icon    = "✂️" if label=="CONSERVATIVA" else "🏥"
    style   = {"fontSize":"26px","fontWeight":"800","color":color,
               "textAlign":"center","margin":"6px 0"}

    return (icon, display, style,
            round(c_cons*100,1), f"{c_cons*100:.1f}%",
            round(c_mast*100,1), f"{c_mast*100:.1f}%",
            f"Modello: {ver}", _history(), "", str(n_clicks))


def _history():
    results = ClassificationRepository.get_all()[:12]
    if not results:
        return html.P("Nessuna classificazione.",
                      style={"color":"#6B7280","fontSize":"13px"})
    return html.Div([
        html.Div([
            html.Span(r["patient_code"],
                      style={"fontWeight":"700","minWidth":"80px","fontSize":"13px"}),
            html.Span(CLASS_DISPLAY.get(r["predicted_class"], r["predicted_class"]),
                      className="badge-bcs" if r["predicted_class"]=="CONSERVATIVA"
                                else "badge-mast"),
            html.Span(r["run_at"],
                      style={"marginLeft":"auto","color":"#9CA3AF","fontSize":"11px"}),
        ], className="hist-row")
        for r in results
    ])
