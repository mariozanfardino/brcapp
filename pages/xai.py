import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
from ml.weka_bridge import (get_feature_importance, get_model_info,
    FEATURES, FEATURE_NAMES, FEATURE_LABELS, FEATURE_GROUPS,
    FEATURE_DESCRIPTIONS, run_classification, get_classifier_name,
    CLASS_DISPLAY, CLASS_COLOR)
from database.db import PatientRepository, ClassificationRepository
from config import PINK, PURPLE

dash.register_page(__name__, path="/xai", name="Explainable AI")

PLOT_CFG = {"displayModeBar": False}
PLOT_LAY = dict(paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=16,r=16,t=30,b=16),
                font=dict(family="Inter,Arial,sans-serif", size=12, color="#374151"))

# ID sicuri senza accenti
def sid(f): return f.replace('à','a').replace('è','e').replace('ì','i').replace('ò','o').replace('ù','u')

layout = html.Div([
    html.Div([
        html.Div([html.H1("Explainable AI",className="page-title"),
                  html.P("Trasparenza, interpretabilità e analisi per singolo paziente",
                         className="page-subtitle")]),
        html.Div(id="xai-badge"),
    ], className="page-topbar"),

    html.Div([
        dbc.Tabs([
            dbc.Tab(label="🔍  Modello",            tab_id="model"),
            dbc.Tab(label="📊  Feature Importance",  tab_id="fi"),
            dbc.Tab(label="🎯  What-If Paziente",    tab_id="whatif"),
            dbc.Tab(label="🧬  Spiegazione locale",  tab_id="local"),
            dbc.Tab(label="📋  Guida clinica",       tab_id="clinical"),
        ], id="xai-tabs", active_tab="model"),
        html.Div(id="xai-content", style={"marginTop":"16px"}),
    ], style={"padding":"20px 24px"}),

    dcc.Interval(id="xai-init", interval=400, n_intervals=0, max_intervals=1),
])


@callback(Output("xai-badge","children"), Input("xai-init","n_intervals"))
def badge(_):
    info = get_model_info(); active = info.get("active",False)
    c = "#059669" if active else "#F59E0B"
    t = "✓  Modello WEKA originale attivo" if active else "⚠  Fallback scikit-learn attivo"
    return html.Span(t, style={"background":c+"22","color":c,"fontWeight":"700",
                                "fontSize":"12px","padding":"6px 14px","borderRadius":"20px"})


@callback(Output("xai-content","children"),
          Input("xai-tabs","active_tab"), Input("xai-init","n_intervals"))
def render(tab, _):
    if tab=="model":   return _tab_model()
    if tab=="fi":      return _tab_fi()
    if tab=="whatif":  return _tab_whatif()
    if tab=="local":   return _tab_local()
    if tab=="clinical":return _tab_clinical()
    return html.Div()


# ── TAB: Modello ──────────────────────────────────────────────────────────────
def _tab_model():
    info = get_model_info()
    fields = [("Algoritmo",info.get("algorithm","—")),("Base learner",info.get("base_learner","—")),
              ("Accuratezza",info.get("accuracy","—")),("Dataset",info.get("dataset_size","—")),
              ("Validazione",info.get("validation","—")),("Classi"," / ".join(info.get("classes",["—"]))),
              ("Paper",info.get("paper","—")),("Autori",info.get("source","—"))]
    metrics = [("Accuratezza","95%",PINK),("Sensibilità","94.5%",PURPLE),
               ("Specificità","96.5%","#059669"),("AUROC","0.98","#0284C7"),
               ("Pazienti","5100","#6B7280"),("Fold CV","10","#6B7280")]
    return dbc.Row([
        dbc.Col([
            html.Div([html.Div("📋  Scheda tecnica",className="card-title"),
                html.Table([html.Tbody([html.Tr([
                    html.Td(k,style={"padding":"9px 14px","fontWeight":"600","color":"#6B7280","fontSize":"13px"}),
                    html.Td(v,style={"padding":"9px 14px","fontSize":"13px","fontWeight":"700"}),
                ],style={"borderBottom":"1px solid #F3F4F6"}) for k,v in fields])],style={"width":"100%"}),
            ],className="card-box mb-3"),
            html.Div([html.Div("🔄  Come funziona AdaBoost",className="card-title"),
                html.Div([html.Div([
                    html.Div(n,style={"width":"26px","height":"26px","borderRadius":"50%","background":PINK,
                                      "color":"white","fontWeight":"700","fontSize":"12px",
                                      "display":"flex","alignItems":"center","justifyContent":"center","flexShrink":"0"}),
                    html.Div([html.Div(t,style={"fontWeight":"700","fontSize":"13px","marginBottom":"2px"}),
                              html.Div(d,style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"})]),
                ],style={"display":"flex","gap":"12px","alignItems":"flex-start","marginBottom":"12px"})
                for n,t,d in [
                    ("1","Feature nominali","Il modello riceve 15 attributi categoriali — non numeri."),
                    ("2","Decision Stump","Ogni weak learner divide su una singola feature con la sua soglia."),
                    ("3","Ensemble ponderato","100 stumps combinati: ogni voto è pesato dalla sua accuratezza."),
                    ("4","Output probabilistico","P(CONSERVATIVA) + P(MASTECTOMIA) = 1."),
                ]]),
            ],className="card-box"),
        ],md=6),
        dbc.Col([
            html.Div([html.Div("📈  Performance BrCaM",className="card-title"),
                html.Div([html.Div([html.Div(v,style={"fontSize":"24px","fontWeight":"800","color":c}),
                    html.Div(k,style={"fontSize":"11px","color":"#6B7280","marginTop":"2px"})],
                    style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px","textAlign":"center"})
                    for k,v,c in metrics],
                    style={"display":"grid","gridTemplateColumns":"repeat(3,1fr)","gap":"10px"}),
            ],className="card-box mb-3"),
            html.Div([html.Div("⚠️  Avvertenze",className="card-title"),
                dbc.Alert(html.Ul([
                    html.Li("Modello retrospettivo — non prescrittivo.",style={"marginBottom":"6px"}),
                    html.Li("Non sostituisce il giudizio clinico.",style={"marginBottom":"6px"}),
                    html.Li("Validato su popolazione italiana (Napoli, 2009-2015)."),
                ],style={"margin":"0","fontSize":"13px","paddingLeft":"16px"}),color="warning"),
            ],className="card-box"),
        ],md=6),
    ],className="g-3")


# ── TAB: Feature Importance ───────────────────────────────────────────────────
def _tab_fi():
    fi    = get_feature_importance()
    items = sorted(fi.items(), key=lambda x:x[1], reverse=True)
    labels= [FEATURE_LABELS.get(k,k) for k,_ in items]
    vals  = [v for _,v in items]; keys=[k for k,_ in items]
    colors= [PINK if v>0.6 else (PURPLE if v>0.45 else "#9CA3AF") for v in vals]
    fig = go.Figure(go.Bar(x=vals,y=labels,orientation="h",marker_color=colors,marker_line_width=0,
        text=[f"{v:.2f}" for v in vals],textposition="outside",textfont_size=11))
    fig.update_layout(**PLOT_LAY,height=430,xaxis=dict(range=[0,1.1],title="Importanza relativa"),
                      yaxis=dict(autorange="reversed"))
    return dbc.Row([
        dbc.Col([html.Div([
            html.Div("Feature Importance globale",className="card-title"),
            dcc.Graph(figure=fig,config=PLOT_CFG),
            html.Div([
                html.Span("■ Alta  ",style={"color":PINK,"fontWeight":"700","fontSize":"12px"}),
                html.Span("■ Media  ",style={"color":PURPLE,"fontWeight":"700","fontSize":"12px"}),
                html.Span("■ Bassa",style={"color":"#9CA3AF","fontWeight":"700","fontSize":"12px"}),
            ],style={"marginTop":"6px"}),
        ],className="card-box")],md=7),
        dbc.Col([html.Div([
            html.Div("Interpretazione per feature",className="card-title"),
            html.Div([html.Div([
                html.Div([html.Span(FEATURE_LABELS.get(k,k),style={"fontWeight":"700","fontSize":"13px"}),
                          html.Span(FEATURE_DESCRIPTIONS.get(k,("",""))[0],
                                    style={"background":PINK+"22" if FEATURE_DESCRIPTIONS.get(k,("",""))[0]=="Alta"
                                           else PURPLE+"22" if FEATURE_DESCRIPTIONS.get(k,("",""))[0]=="Media" else "#F3F4F6",
                                           "color":PINK if FEATURE_DESCRIPTIONS.get(k,("",""))[0]=="Alta"
                                           else PURPLE if FEATURE_DESCRIPTIONS.get(k,("",""))[0]=="Media" else "#6B7280",
                                           "fontSize":"10px","fontWeight":"700","padding":"2px 8px",
                                           "borderRadius":"10px","marginLeft":"8px"})],
                         style={"display":"flex","alignItems":"center","marginBottom":"3px"}),
                html.Div(FEATURE_DESCRIPTIONS.get(k,("",""))[1],
                         style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"}),
            ],style={"padding":"9px 0","borderBottom":"1px solid #F3F4F6"}) for k in keys[:8]]),
        ],className="card-box")],md=5),
    ],className="g-3")


# ── TAB: What-If Paziente ─────────────────────────────────────────────────────
def _tab_whatif():
    pts = PatientRepository.get_all()
    opts = [{"label":"— Seleziona paziente —","value":""}] + \
           [{"label":f"{p['code']}  ({p.get('biRadsClinico','?')})","value":p["id"]} for p in pts]

    # Feature di interesse per what-if (evita quelle con troppi valori)
    WI_FEATURES = ["stato_linfonodaleDX","stato_linfonodaleSX","biRadsClinico",
                   "focalità","citologia_codifica","struttura_ghiandolare",
                   "rapporto_cuteDX","ricostruzione"]

    dropdowns = []
    for feat in WI_FEATURES:
        vals = FEATURES.get(feat,[])
        fid  = sid(feat)
        dropdowns.append(dbc.Col([
            dbc.Label(FEATURE_LABELS.get(feat,feat),className="form-label",
                      style={"fontSize":"12px"}),
            dbc.Select(id=f"wi-{fid}",
                options=[{"label":v,"value":v} for v in vals],
                value=""),
        ],md=6,style={"marginBottom":"10px"}))

    return dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Seleziona paziente di partenza",className="card-title"),
                dcc.Dropdown(id="wi-patient-select",options=opts,value="",
                             placeholder="— Paziente —",style={"fontSize":"13px","marginBottom":"16px"}),
                html.Div("Modifica i valori per vedere come cambia la predizione:",
                         style={"fontSize":"12px","color":"#6B7280","marginBottom":"12px"}),
                dbc.Row(dropdowns),
                dbc.Button("🔄  Calcola variazione",id="btn-wi-calc",
                           className="btn-pink w-100 mt-2"),
            ],className="card-box"),
        ],md=6),
        dbc.Col([
            html.Div([html.Div("Risultato What-If",className="card-title"),
                      html.Div(id="wi-result-box")],className="card-box mb-3"),
            html.Div([html.Div("Sensitivity per feature",className="card-title"),
                      dcc.Graph(id="wi-sens-chart",config=PLOT_CFG,style={"height":"320px"})],
                     className="card-box"),
        ],md=6),
    ],className="g-3")


# ── TAB: Spiegazione locale ───────────────────────────────────────────────────
def _tab_local():
    pts  = PatientRepository.get_all()
    clfs = ClassificationRepository.get_all()[:30]
    clf_opts = [{"label":"— Seleziona classificazione —","value":""}]
    for c in clfs:
        clf_opts.append({"label":f"{c['patient_code']}  →  {c['predicted_class']}  ({c['run_at']})",
                         "value":c["id"]})
    return dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Analisi locale — singola classificazione",className="card-title"),
                html.P("Seleziona una classificazione per vedere quali feature hanno avuto più peso "
                       "per quel singolo paziente.",
                       style={"fontSize":"12px","color":"#6B7280","marginBottom":"12px"}),
                dcc.Dropdown(id="local-clf-select",options=clf_opts,value="",
                             placeholder="— Seleziona —",style={"fontSize":"13px"}),
                dbc.Button("🧬  Analizza",id="btn-local-analyze",
                           className="btn-pink mt-3",disabled=True),
            ],className="card-box"),
        ],md=4),
        dbc.Col([
            html.Div([html.Div("Contributo feature per questo paziente",className="card-title"),
                      html.Div(id="local-result")],className="card-box"),
        ],md=8),
    ],className="g-3")


# ── TAB: Guida clinica ────────────────────────────────────────────────────────
def _tab_clinical():
    fi    = get_feature_importance()
    items = sorted(fi.items(),key=lambda x:x[1],reverse=True)
    def ccard(feat,imp):
        lbl=FEATURE_LABELS.get(feat,feat); pct=int(imp*100)
        c=PINK if imp>0.6 else (PURPLE if imp>0.45 else "#9CA3AF")
        desc=FEATURE_DESCRIPTIONS.get(feat,("",""))[1]
        return html.Div([
            html.Div([html.Span(lbl,style={"fontWeight":"700","fontSize":"13px"}),
                      html.Span(f"{pct}%",style={"color":c,"fontWeight":"800",
                                                  "marginLeft":"auto","fontSize":"14px"})],
                     style={"display":"flex","marginBottom":"5px"}),
            html.Div(style={"background":"#F0F0F0","borderRadius":"20px","height":"6px","overflow":"hidden","marginBottom":"5px"},
                     children=[html.Div(style={"width":f"{pct}%","background":c,"height":"100%","borderRadius":"20px"})]),
            html.Div(desc,style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"}),
        ],style={"padding":"10px 0","borderBottom":"1px solid #F3F4F6"})
    return dbc.Row([
        dbc.Col([html.Div([html.Div("🩺  Regole cliniche del modello",className="card-title"),
            *[ccard(k,v) for k,v in items]],className="card-box")],md=7),
        dbc.Col([html.Div([html.Div("📖  Valori accettati per feature",className="card-title"),
            *[html.Div([
                html.Div(FEATURE_LABELS.get(k,k),style={"fontWeight":"700","fontSize":"13px"}),
                html.Div(", ".join(FEATURES.get(k,[])),
                         style={"fontSize":"11px","color":"#6B7280","lineHeight":"1.5","marginTop":"2px"}),
            ],style={"padding":"9px 0","borderBottom":"1px solid #F3F4F6"}) for k in FEATURE_NAMES]
        ],className="card-box")],md=5),
    ],className="g-3")


# ── Callbacks What-If ─────────────────────────────────────────────────────────
WI_FEATS = ["stato_linfonodaleDX","stato_linfonodaleSX","biRadsClinico",
            "focalità","citologia_codifica","struttura_ghiandolare",
            "rapporto_cuteDX","ricostruzione"]

@callback(
    *[Output(f"wi-{sid(f)}","value") for f in WI_FEATS],
    Input("wi-patient-select","value"),
    prevent_initial_call=True,
)
def prefill_wi(pid):
    empty = [""] * len(WI_FEATS)
    if not pid: return empty
    pts = PatientRepository.get_all()
    p   = next((x for x in pts if x.get("id")==int(pid)), {})
    mapping = {
        "stato_linfonodaleDX":   p.get("stato_linfonodaleDX",""),
        "stato_linfonodaleSX":   p.get("stato_linfonodaleSX",""),
        "biRadsClinico":         p.get("biRadsClinico",""),
        "focalità":              p.get("focalita",""),
        "citologia_codifica":    p.get("citologia_codifica",""),
        "struttura_ghiandolare": p.get("struttura_ghiandolare",""),
        "rapporto_cuteDX":       p.get("rapporto_cuteDX",""),
        "ricostruzione":         p.get("ricostruzione",""),
    }
    return [mapping.get(f,"") for f in WI_FEATS]


@callback(
    Output("wi-result-box","children"),
    Output("wi-sens-chart","figure"),
    Input("btn-wi-calc","n_clicks"),
    State("wi-patient-select","value"),
    *[State(f"wi-{sid(f)}","value") for f in WI_FEATS],
    prevent_initial_call=True,
)
def calc_wi(n, pid, *wi_vals):
    if not n: return dash.no_update, dash.no_update
    wi_map = {f: v for f,v in zip(WI_FEATS, wi_vals)}

    # Base patient features
    base = {}
    if pid:
        pts = PatientRepository.get_all()
        p   = next((x for x in pts if x.get("id")==int(pid)), {})
        # Mappa tutti i feature names al valore del paziente
        feat_map = {
            "età":                           p.get("age_range","18-25"),
            "fumo":                          p.get("fumo","no"),
            "gravidanza":                    p.get("gravidanza","no"),
            "familiarità_carcinoma_ovarico": p.get("familiarita_carcinoma_ovarico","no"),
            "struttura_ghiandolare":         p.get("struttura_ghiandolare","Normale"),
            "rapporto_cuteDX":               p.get("rapporto_cuteDX","Regolare"),
            "rapporto_cuteSX":               p.get("rapporto_cuteSX","Regolare"),
            "rapporto_areola_capezzoloDX":   p.get("rapporto_areola_capezzoloDX","Regolare"),
            "rapporto_areola_capezzoloSX":   p.get("rapporto_areola_capezzoloSX","Regolare"),
            "stato_linfonodaleDX":           p.get("stato_linfonodaleDX","Normale"),
            "stato_linfonodaleSX":           p.get("stato_linfonodaleSX","Normale"),
            "biRadsClinico":                 p.get("biRadsClinico","E3"),
            "citologia_codifica":            p.get("citologia_codifica","no"),
            "focalità":                      p.get("focalita","no"),
            "ricostruzione":                 p.get("ricostruzione","no"),
        }
        base = feat_map
    else:
        base = {f: FEATURES[f][0] for f in FEATURE_NAMES}

    # Applica variazioni what-if
    modified = {**base}
    for feat, val in wi_map.items():
        key = feat if feat in FEATURE_NAMES else None
        if not key: continue
        if val and val in FEATURES.get(feat,[]):
            modified[key] = val

    # Verifica completezza
    for f in FEATURE_NAMES:
        if not modified.get(f) or modified[f] not in FEATURES.get(f,[]):
            modified[f] = FEATURES[f][0]

    label, c_cons, c_mast, ver = run_classification(modified)
    color  = CLASS_COLOR.get(label,"#6B7280")
    disp   = CLASS_DISPLAY.get(label, label)
    icon   = "✂️" if label=="CONSERVATIVA" else "🏥"

    result = html.Div([
        html.Div(icon, style={"fontSize":"40px","textAlign":"center"}),
        html.Div(disp, style={"fontSize":"24px","fontWeight":"800","color":color,
                               "textAlign":"center","margin":"8px 0"}),
        html.Div([
            html.Div([
                html.Span("Conservativa", style={"fontSize":"13px","minWidth":"100px"}),
                dbc.Progress(value=round(c_cons*100,1),color="success",
                             style={"flex":"1","height":"12px","borderRadius":"6px"}),
                html.Span(f"{c_cons*100:.1f}%", style={"minWidth":"46px","fontWeight":"700",
                                                         "color":"#059669","fontSize":"13px"}),
            ], style={"display":"flex","alignItems":"center","gap":"10px","marginBottom":"8px"}),
            html.Div([
                html.Span("Mastectomia", style={"fontSize":"13px","minWidth":"100px"}),
                dbc.Progress(value=round(c_mast*100,1),color="danger",
                             style={"flex":"1","height":"12px","borderRadius":"6px"}),
                html.Span(f"{c_mast*100:.1f}%", style={"minWidth":"46px","fontWeight":"700",
                                                         "color":"#DC2626","fontSize":"13px"}),
            ], style={"display":"flex","alignItems":"center","gap":"10px"}),
        ], style={"marginTop":"14px"}),
        html.Div(f"Modello: {ver}", style={"fontSize":"11px","color":"#9CA3AF",
                                            "textAlign":"center","marginTop":"10px"}),
    ])

    # Sensitivity: varia ogni WI feature sui suoi valori possibili
    deltas = []
    for feat in WI_FEATS:
        vals = FEATURES.get(feat,[])
        probs = []
        for v in vals[:8]:  # max 8 valori
            test = {**modified, feat: v}
            _, c, _, _ = run_classification(test)
            probs.append(c)
        deltas.append(max(probs)-min(probs) if probs else 0)

    fig = go.Figure(go.Bar(
        x=[FEATURE_LABELS.get(f,f) for f in WI_FEATS],
        y=deltas, marker_color=PINK, marker_line_width=0,
        text=[f"{d:.3f}" for d in deltas], textposition="outside",
    ))
    fig.update_layout(**PLOT_LAY, height=300,
                      yaxis_title="Δ max P(Conservativa)", xaxis_tickangle=-25)

    return result, fig


# ── Callbacks Local explanation ───────────────────────────────────────────────
@callback(Output("btn-local-analyze","disabled"),
          Input("local-clf-select","value"))
def toggle_analyze(v): return not bool(v)


@callback(
    Output("local-result","children"),
    Input("btn-local-analyze","n_clicks"),
    State("local-clf-select","value"),
    prevent_initial_call=True,
)
def local_explain(n, clf_id):
    if not clf_id: return html.Div()
    clfs = ClassificationRepository.get_all()
    clf  = next((c for c in clfs if c.get("id")==int(clf_id)), None)
    if not clf: return html.P("Classificazione non trovata.")

    import json
    snap = {}
    try:
        all_clfs = ClassificationRepository.get_all()
        c = next((x for x in all_clfs if x["id"]==int(clf_id)), None)
        # Input snapshot è stringa JSON
        from database.db import read_scope
        from database.models import ClassificationResult
        with read_scope() as db:
            cr = db.query(ClassificationResult).filter(ClassificationResult.id==int(clf_id)).first()
            if cr and cr.input_snapshot:
                snap = json.loads(cr.input_snapshot)
    except Exception:
        pass

    if not snap:
        return dbc.Alert("Snapshot input non disponibile per questa classificazione.",color="warning")

    # Sensitivity locale: per ogni feature, prova tutti i valori alternativi
    fi_global = get_feature_importance()
    local_impact = []
    for feat in FEATURE_NAMES:
        if feat not in snap: continue
        current_val = snap[feat]
        current_label, c_base, _, _ = run_classification(snap)
        max_delta = 0
        worst_val = current_val
        for alt_val in FEATURES.get(feat,[]):
            if alt_val == current_val: continue
            test = {**snap, feat: alt_val}
            _, c_alt, _, _ = run_classification(test)
            delta = abs(c_alt - c_base)
            if delta > max_delta:
                max_delta = delta; worst_val = alt_val
        local_impact.append((feat, current_val, max_delta, worst_val, fi_global.get(feat,0)))

    local_impact.sort(key=lambda x:x[2], reverse=True)

    pred  = clf.get("predicted_class","—")
    color = CLASS_COLOR.get(pred,"#6B7280")
    disp  = CLASS_DISPLAY.get(pred,pred)

    rows = [
        html.Tr([html.Th(h,style={"background":"#EDE7F6","color":"#4A235A","fontWeight":"700",
                                   "fontSize":"11px","padding":"8px 12px","textTransform":"uppercase"})
                 for h in ["Feature","Valore paziente","Impatto locale","Val. più impattante"]])
    ]
    for feat, val, delta, worst, fi in local_impact:
        bar_w = int(delta*200)
        rows.append(html.Tr([
            html.Td(FEATURE_LABELS.get(feat,feat),style={"padding":"9px 12px","fontWeight":"600","fontSize":"13px"}),
            html.Td(html.Span(str(val),style={"background":PURPLE+"22","color":PURPLE,
                                               "padding":"2px 8px","borderRadius":"10px","fontSize":"12px","fontWeight":"700"}),
                    style={"padding":"9px 12px"}),
            html.Td([
                html.Div(style={"width":f"{min(bar_w,200)}px","height":"8px","background":PINK,
                                 "borderRadius":"4px","display":"inline-block"}),
                html.Span(f"  {delta:.3f}",style={"fontSize":"11px","color":"#6B7280","marginLeft":"6px"}),
            ],style={"padding":"9px 12px"}),
            html.Td(html.Span(str(worst),style={"background":"#FEE2E2","color":"#DC2626",
                                                  "padding":"2px 8px","borderRadius":"10px",
                                                  "fontSize":"12px"}) if worst!=val else "—",
                    style={"padding":"9px 12px"}),
        ],style={"borderBottom":"1px solid #F3F4F6"}))

    return html.Div([
        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Predizione",style={"fontSize":"11px","color":"#6B7280"}),
                html.Div(disp,style={"fontSize":"20px","fontWeight":"800","color":color}),
            ],style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}),md=4),
            dbc.Col(html.Div([
                html.Div("Confidence conservativa",style={"fontSize":"11px","color":"#6B7280"}),
                html.Div(f"{clf.get('confidence_bcs','—')}%",
                         style={"fontSize":"20px","fontWeight":"800","color":"#059669"}),
            ],style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}),md=4),
            dbc.Col(html.Div([
                html.Div("Paziente",style={"fontSize":"11px","color":"#6B7280"}),
                html.Div(clf.get("patient_code","—"),style={"fontSize":"20px","fontWeight":"800"}),
            ],style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px"}),md=4),
        ],className="g-2 mb-3"),
        html.P("Le feature con impatto locale più alto sono quelle che, se cambiate, modificherebbero "
               "di più la predizione per questo specifico paziente.",
               style={"fontSize":"12px","color":"#6B7280","marginBottom":"10px"}),
        html.Table(rows,style={"width":"100%","borderCollapse":"collapse"}),
    ])
