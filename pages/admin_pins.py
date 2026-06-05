import dash
from dash import html, dcc, callback, Output, Input, ALL, ctx
import dash_bootstrap_components as dbc
from database.auth_db import PatientAuthRepository, generate_pin

dash.register_page(__name__, path="/admin/pins", name="PIN Pazienti")

def _table():
    patients = PatientAuthRepository.get_all_with_pin_status()
    if not patients:
        return html.P("Nessun paziente nel database.",
                      style={"color":"#6B7280","padding":"20px"})
    rows = [html.Tr([
        html.Th(h, style={"background":"#EDE7F6","color":"#4A235A",
                           "fontWeight":"700","fontSize":"11px",
                           "padding":"10px 14px","textTransform":"uppercase"})
        for h in ["Codice","Iniziali","PIN","Azione"]
    ])] + [
        html.Tr([
            html.Td(p["code"],    style={"padding":"10px 14px","fontWeight":"700"}),
            html.Td(p["initials"],style={"padding":"10px 14px","color":"#6B7280"}),
            html.Td(
                html.Span("✓  Attivo"       if p["has_pin"] else "✗  Non impostato",
                          style={"color": "#059669" if p["has_pin"] else "#DC2626",
                                 "fontWeight":"700","fontSize":"12px"}),
                style={"padding":"10px 14px"}),
            html.Td(
                dbc.Button("🔑  Genera nuovo PIN",
                           id={"type":"gen-pin","id":p["id"]},
                           size="sm", className="btn-outline-purple"),
                style={"padding":"6px 14px"}),
        ], style={"borderBottom":"1px solid #F3F4F6",
                  "background":"white" if i%2==0 else "#FAFAFA"})
        for i,p in enumerate(patients)
    ]
    return html.Table(rows, style={"width":"100%","borderCollapse":"collapse"})


layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Accesso Pazienti — PIN", className="page-title"),
            html.P("Genera e gestisci i PIN per l'accesso dei pazienti all'area personale",
                   className="page-subtitle"),
        ]),
    ], className="page-topbar"),

    html.Div([
        # Istruzioni
        dbc.Alert([
            html.Strong("Come funziona: "),
            "Genera un PIN per ogni paziente e comunicaglielo. "
            "Il paziente accede su ",
            html.Code("/patient/login"),
            " con il proprio codice paziente e il PIN. "
            "Ogni nuovo PIN generato invalida il precedente.",
        ], color="info", style={"marginBottom":"20px","fontSize":"13px"}),

        # Risultato generazione
        html.Div(id="pin-result-main"),

        # Tabella
        html.Div(id="pin-table", children=_table()),

    ], style={"padding":"20px 24px"}),
])


@callback(
    Output("pin-result-main","children"),
    Output("pin-table","children"),
    Input({"type":"gen-pin","id":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def gen_pin(n_clicks):
    tid = ctx.triggered_id
    if not isinstance(tid, dict) or not any(n_clicks):
        return dash.no_update, _table()
    pid  = tid["id"]
    pin  = generate_pin()
    PatientAuthRepository.set_pin(pid, pin)
    pts  = PatientAuthRepository.get_all_with_pin_status()
    code = next((p["code"] for p in pts if p["id"]==pid), "?")
    alert = dbc.Alert([
        html.Div([
            html.Strong(f"PIN generato per il paziente  {code}",
                        style={"fontSize":"15px"}),
        ], style={"marginBottom":"10px"}),
        html.Div(pin, style={"fontSize":"36px","fontWeight":"800",
                             "letterSpacing":"10px","fontFamily":"monospace",
                             "color":"#1A1A2E","background":"white",
                             "display":"inline-block","padding":"8px 24px",
                             "borderRadius":"10px","border":"2px solid #059669"}),
        html.Div("Comunica questo PIN al paziente. Non verrà più visualizzato.",
                 style={"marginTop":"10px","fontSize":"12px","color":"#6B7280"}),
    ], color="success", dismissable=True, style={"marginBottom":"16px"})
    return alert, _table()
