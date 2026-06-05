
import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
from ml.weka_bridge import (get_feature_importance, get_model_info,
    FEATURE_LABELS, FEATURE_DESCRIPTIONS, FEATURE_NAMES,
    run_classification, get_classifier_name)
from config import PINK, PURPLE

dash.register_page(__name__, path="/xai", name="Explainable AI")
PLOT_CFG={"displayModeBar":False}
PLOT_LAY=dict(paper_bgcolor="white",plot_bgcolor="white",
    margin=dict(l=16,r=16,t=30,b=16),
    font=dict(family="Inter,Arial,sans-serif",size=12,color="#374151"))

DEFAULT_INPUT={
    "age":55.0,"bmi":27.0,"tumor_size_mm":25.0,"tumor_quadrant":2.0,
    "histology_type":1.0,"grade":2.0,"er_status":1.0,"pr_status":1.0,
    "her2_status":0.0,"ki67_percent":25.0,"multifocality":0.0,
    "lymph_node_positive":0.0,"eating_habit_score":6.0,"physical_activity":5.0,
}

layout=html.Div([
    html.Div([
        html.Div([html.H1("Explainable AI",className="page-title"),
                  html.P("Trasparenza e interpretabilità del modello BrCaM",className="page-subtitle")]),
        html.Div(id="xai-badge"),
    ],className="page-topbar"),
    html.Div([
        dbc.Tabs([
            dbc.Tab(label="🔍  Modello",           tab_id="model"),
            dbc.Tab(label="📊  Feature Importance",  tab_id="fi"),
            dbc.Tab(label="🎯  What-If",            tab_id="whatif"),
            dbc.Tab(label="📋  Guida clinica",      tab_id="clinical"),
        ],id="xai-tabs",active_tab="model"),
        html.Div(id="xai-content",style={"marginTop":"16px"}),
    ],style={"padding":"20px 24px"}),
    dcc.Interval(id="xai-init",interval=400,n_intervals=0,max_intervals=1),
])

@callback(Output("xai-badge","children"),Input("xai-init","n_intervals"))
def badge(_):
    info=get_model_info(); active=info.get("active",False)
    c="#059669" if active else "#F59E0B"
    t="✓  Modello WEKA originale attivo" if active else "⚠  Fallback scikit-learn attivo"
    return html.Span(t,style={"background":c+"22","color":c,"fontWeight":"700",
                               "fontSize":"12px","padding":"6px 14px","borderRadius":"20px"})

@callback(Output("xai-content","children"),
          Input("xai-tabs","active_tab"),Input("xai-init","n_intervals"))
def render(tab,_):
    if tab=="model":   return tab_model()
    if tab=="fi":      return tab_fi()
    if tab=="whatif":  return tab_whatif()
    if tab=="clinical":return tab_clinical()
    return html.Div()

def tab_model():
    info=get_model_info()
    fields=[("Algoritmo",info.get("algorithm","—")),("Base learner",info.get("base_learner","—")),
            ("Accuratezza",info.get("accuracy","—")),("Dataset",info.get("dataset_size","—")),
            ("Validazione",info.get("validation","—")),("Classi"," / ".join(info.get("classes",["—"]))),
            ("Paper",info.get("paper","—")),("Autori",info.get("source","—"))]
    steps=[("1","Weak learner iniziale","Decision Stump: un albero con un solo split su una feature."),
           ("2","Pesatura errori","Esempi classificati male ricevono peso maggiore all iterazione successiva."),
           ("3","Ensemble ponderato","100 weak learner combinati con voto pesato dalla loro accuratezza."),
           ("4","Output probabilistico","Somma pesata produce P(BCS) e P(Mastectomy).")]
    metrics=[("Accuratezza","95%",PINK),("Sensibilità","94%",PURPLE),
             ("Specificità","96%","#059669"),("AUC-ROC","0.97","#0284C7"),
             ("Pazienti","5100","#6B7280"),("Fold CV","10","#6B7280")]
    return dbc.Row([
        dbc.Col([
            html.Div([html.Div("📋  Scheda tecnica",className="card-title"),
                html.Table([html.Tbody([html.Tr([
                    html.Td(k,style={"padding":"9px 14px","fontWeight":"600","color":"#6B7280","fontSize":"13px"}),
                    html.Td(v,style={"padding":"9px 14px","fontSize":"13px","fontWeight":"700"}),
                ],style={"borderBottom":"1px solid #F3F4F6"}) for k,v in fields])],
                style={"width":"100%"}),
            ],className="card-box mb-3"),
            html.Div([html.Div("🔄  Come funziona AdaBoost",className="card-title"),
                *[html.Div([html.Div([
                    html.Div(n,style={"width":"26px","height":"26px","borderRadius":"50%","background":PINK,
                                      "color":"white","fontWeight":"700","fontSize":"12px","display":"flex",
                                      "alignItems":"center","justifyContent":"center","flexShrink":"0"}),
                    html.Div([html.Div(t,style={"fontWeight":"700","fontSize":"13px","marginBottom":"2px"}),
                              html.Div(d,style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"})]),
                ],style={"display":"flex","gap":"12px","alignItems":"flex-start"}),
                ],style={"marginBottom":"12px"}) for n,t,d in steps],
            ],className="card-box"),
        ],md=6),
        dbc.Col([
            html.Div([html.Div("📈  Performance BrCaM",className="card-title"),
                html.Div([html.Div([
                    html.Div(v,style={"fontSize":"24px","fontWeight":"800","color":c}),
                    html.Div(k,style={"fontSize":"11px","color":"#6B7280","marginTop":"2px"}),
                ],style={"background":"#F4F6F9","borderRadius":"10px","padding":"14px","textAlign":"center"})
                for k,v,c in metrics],
                style={"display":"grid","gridTemplateColumns":"repeat(3,1fr)","gap":"10px"}),
            ],className="card-box mb-3"),
            html.Div([html.Div("⚠️  Avvertenze",className="card-title"),
                dbc.Alert(html.Ul([
                    html.Li("Modello retrospettivo: cattura pattern storici, non linee guida prospettiche.",style={"marginBottom":"6px"}),
                    html.Li("Non sostituisce il giudizio clinico.",style={"marginBottom":"6px"}),
                    html.Li("Validato su popolazione italiana.",style={"marginBottom":"6px"}),
                    html.Li("Variabile eating_habit_score è specifica di BrCaM."),
                ],style={"margin":"0","fontSize":"13px","paddingLeft":"16px"}),color="warning"),
            ],className="card-box"),
        ],md=6),
    ],className="g-3")

def tab_fi():
    fi=get_feature_importance()
    items=sorted(fi.items(),key=lambda x:x[1],reverse=True)
    labels=[FEATURE_LABELS.get(k,k) for k,_ in items]
    vals=[v for _,v in items]; keys=[k for k,_ in items]
    colors=[PINK if v>0.6 else (PURPLE if v>0.45 else "#9CA3AF") for v in vals]
    fig=go.Figure(go.Bar(x=vals,y=labels,orientation="h",marker_color=colors,marker_line_width=0,
        text=[f"{v:.2f}" for v in vals],textposition="outside",textfont_size=11))
    fig.update_layout(**PLOT_LAY,height=430,
        xaxis=dict(range=[0,1.1],title="Importanza relativa"),yaxis=dict(autorange="reversed"))
    return dbc.Row([
        dbc.Col([html.Div([
            html.Div("Feature Importance — contributo di ogni variabile",className="card-title"),
            dcc.Graph(figure=fig,config=PLOT_CFG),
            html.Div([html.Span("■ Alta  ",style={"color":PINK,"fontWeight":"700","fontSize":"12px"}),
                      html.Span("■ Media  ",style={"color":PURPLE,"fontWeight":"700","fontSize":"12px"}),
                      html.Span("■ Bassa",style={"color":"#9CA3AF","fontWeight":"700","fontSize":"12px"})],
                     style={"marginTop":"8px"}),
        ],className="card-box")],md=7),
        dbc.Col([html.Div([
            html.Div("Interpretazione",className="card-title"),
            html.Div([html.Div([
                html.Div([html.Span(FEATURE_LABELS.get(k,k),style={"fontWeight":"700","fontSize":"13px"}),
                          html.Span(FEATURE_DESCRIPTIONS[k][0],style={"background":
                              PINK+"22" if FEATURE_DESCRIPTIONS[k][0]=="Alta" else
                              PURPLE+"22" if FEATURE_DESCRIPTIONS[k][0]=="Media" else "#F3F4F6",
                              "color":PINK if FEATURE_DESCRIPTIONS[k][0]=="Alta" else
                              PURPLE if FEATURE_DESCRIPTIONS[k][0]=="Media" else "#6B7280",
                              "fontSize":"10px","fontWeight":"700","padding":"2px 8px",
                              "borderRadius":"10px","marginLeft":"8px"})],
                         style={"display":"flex","alignItems":"center","marginBottom":"3px"}),
                html.Div(FEATURE_DESCRIPTIONS[k][1],style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"}),
            ],style={"padding":"9px 0","borderBottom":"1px solid #F3F4F6"}) for k in keys[:8]]),
        ],className="card-box")],md=5),
    ],className="g-3")

def tab_whatif():
    fi=get_feature_importance()
    top5=sorted(fi.items(),key=lambda x:x[1],reverse=True)[:5]
    sliders=[]
    ranges={"tumor_size_mm":(1,80,0.5),"grade":(1,3,1),"ki67_percent":(0,100,1),
            "age":(18,90,1),"bmi":(15,45,0.5),"multifocality":(0,1,1),
            "lymph_node_positive":(0,1,1),"er_status":(0,1,1),"physical_activity":(0,10,0.5)}
    for feat,_ in top5:
        lo,hi,step=ranges.get(feat,(0,10,0.5))
        sliders.append(html.Div([
            html.Div([html.Span(FEATURE_LABELS.get(feat,feat),style={"fontWeight":"600","fontSize":"13px"}),
                      html.Span(id=f"wiv-{feat}",style={"color":PINK,"fontWeight":"700","marginLeft":"8px"})],
                     style={"display":"flex","justifyContent":"space-between","marginBottom":"4px"}),
            dcc.Slider(id=f"wi-{feat}",min=lo,max=hi,step=step,value=DEFAULT_INPUT.get(feat,(lo+hi)/2),
                       marks=None,tooltip={"always_visible":False}),
        ],style={"marginBottom":"16px"}))
    return dbc.Row([
        dbc.Col([html.Div([
            html.Div("🎛  Muovi i cursori per vedere come cambia la predizione",className="card-title"),
            html.Div("Analisi basata sulle 5 feature più importanti.",
                     style={"fontSize":"12px","color":"#6B7280","marginBottom":"16px"}),
            *sliders,
        ],className="card-box")],md=5),
        dbc.Col([
            html.Div([html.Div("Risultato What-If",className="card-title"),html.Div(id="wi-result")],
                     className="card-box mb-3"),
            html.Div([html.Div("Sensitivity — impatto ±10% di ogni feature",className="card-title"),
                      dcc.Graph(id="wi-sens",config=PLOT_CFG,style={"height":"260px"})],
                     className="card-box"),
        ],md=7),
    ],className="g-3")

def tab_clinical():
    fi=get_feature_importance()
    items=sorted(fi.items(),key=lambda x:x[1],reverse=True)
    def ccard(feat,imp):
        lbl=FEATURE_LABELS.get(feat,feat); pct=int(imp*100)
        c=PINK if imp>0.6 else (PURPLE if imp>0.45 else "#9CA3AF")
        desc=FEATURE_DESCRIPTIONS.get(feat,("",""))[1]
        return html.Div([
            html.Div([html.Span(lbl,style={"fontWeight":"700","fontSize":"13px"}),
                      html.Span(f"{pct}%",style={"color":c,"fontWeight":"800","marginLeft":"auto","fontSize":"14px"})],
                     style={"display":"flex","marginBottom":"5px"}),
            html.Div(style={"background":"#F0F0F0","borderRadius":"20px","height":"6px","overflow":"hidden","marginBottom":"5px"},
                     children=[html.Div(style={"width":f"{pct}%","background":c,"height":"100%","borderRadius":"20px"})]),
            html.Div(desc,style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5"}),
        ],style={"padding":"10px 0","borderBottom":"1px solid #F3F4F6"})
    return dbc.Row([
        dbc.Col([html.Div([
            html.Div("🩺  Regole cliniche apprese dal modello",className="card-title"),
            html.Div("Il modello ha interiorizzato questi criteri dagli storici chirurgici.",
                     style={"fontSize":"12px","color":"#6B7280","marginBottom":"12px"}),
            *[ccard(k,v) for k,v in items],
        ],className="card-box")],md=7),
        dbc.Col([html.Div([
            html.Div("📖  Glossario",className="card-title"),
            *[html.Div([
                html.Div(FEATURE_LABELS.get(k,k),style={"fontWeight":"700","fontSize":"13px"}),
                html.Div(FEATURE_DESCRIPTIONS[k][1],style={"fontSize":"12px","color":"#6B7280","lineHeight":"1.5","marginTop":"2px"}),
            ],style={"padding":"9px 0","borderBottom":"1px solid #F3F4F6"}) for k in FEATURE_NAMES],
        ],className="card-box")],md=5),
    ],className="g-3")

# Callbacks What-If
_fi=get_feature_importance()
_top5=sorted(_fi.items(),key=lambda x:x[1],reverse=True)[:5]
_k5=[k for k,_ in _top5]

@callback(
    Output("wi-result","children"), Output("wi-sens","figure"),
    *[Output(f"wiv-{k}","children") for k in _k5],
    *[Input(f"wi-{k}","value") for k in _k5],
)
def whatif_cb(*vals):
    inp={k:float(v) for k,v in zip(_k5,vals) if v is not None}
    full={**DEFAULT_INPUT,**inp}
    lbl,cb,cm,_=run_classification(full)
    col={"BCS":"#059669","Mastectomy":"#DC2626"}.get(lbl,"#6B7280")
    ico={"BCS":"✂️","Mastectomy":"🏥"}.get(lbl,"?")
    result=html.Div([
        html.Div(ico,style={"fontSize":"40px","textAlign":"center"}),
        html.Div(lbl,style={"fontSize":"28px","fontWeight":"800","color":col,"textAlign":"center","margin":"6px 0"}),
        *[html.Div([
            html.Div([html.Span(lb,style={"fontSize":"13px","minWidth":"90px"}),
                      html.Div(style={"flex":"1","background":"#F0F0F0","borderRadius":"6px","height":"12px","overflow":"hidden"},
                               children=[html.Div(style={"width":f"{round(v*100,1)}%","background":c,"height":"100%","borderRadius":"6px"})]),
                      html.Span(f"{round(v*100,1)}%",style={"minWidth":"44px","textAlign":"right","fontWeight":"700","color":c,"fontSize":"13px"})],
                     style={"display":"flex","alignItems":"center","gap":"10px","marginBottom":"8px"}),
        ]) for lb,v,c in [("BCS",cb,"#059669"),("Mastectomy",cm,"#DC2626")]],
    ])
    deltas=[]
    for feat in _k5:
        bv=float(full.get(feat,0))
        try:
            _,u,_,_=run_classification({**full,feat:bv*1.1+0.01})
            _,d,_,_=run_classification({**full,feat:max(0,bv*0.9-0.01)})
            deltas.append(abs(u-d))
        except: deltas.append(0)
    fig=go.Figure(go.Bar(x=[FEATURE_LABELS.get(k,k) for k in _k5],y=deltas,
        marker_color=PINK,marker_line_width=0,
        text=[f"{d:.3f}" for d in deltas],textposition="outside"))
    fig.update_layout(**PLOT_LAY,height=240,yaxis_title="Δ conf. BCS",xaxis_tickangle=-20)
    return (result,fig,*[f"{v:.1f}" for v in vals])
