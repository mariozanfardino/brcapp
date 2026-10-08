import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from flask import session
from database import portal_db
from auth.session import login_patient
from services.notifications import send_verification
from services.audit import audit
from config import FACILITY_NAME

dash.register_page(__name__, path="/patient/register", name="Portale Paziente — Registrazione")

INFORMATIVA = (f"Il Titolare del trattamento ({FACILITY_NAME}) tratta i tuoi dati personali e "
               "sanitari (art. 9 GDPR) esclusivamente per finalità di cura e per l'erogazione del "
               "servizio di consultazione online. I dati sono accessibili solo al personale "
               "autorizzato, ogni accesso è registrato e puoi esercitare i diritti degli artt. 15-22 "
               "GDPR contattando la struttura.")


def layout(**kwargs):
    pending = session.get("pending_oauth")
    email_field = (
        [dbc.Label("Email", className="form-label"),
         dbc.Input(id="rg-email", type="email", value=pending["email"], disabled=True,
                   style={"marginBottom": "6px", "height": "40px"}),
         html.Div(f"Accesso con {pending['provider'].title()}: non serve una password.",
                  className="pw-hint", style={"margin": "0 0 14px"}),
         dbc.Input(id="rg-pw", type="hidden", value=""), dbc.Input(id="rg-pw2", type="hidden", value="")]
        if pending else
        [dbc.Label("Email", className="form-label"),
         dbc.Input(id="rg-email", type="email", placeholder="nome@esempio.it", autoComplete="email",
                   style={"marginBottom": "14px", "height": "40px"}),
         dbc.Label("Password", className="form-label"),
         dbc.Input(id="rg-pw", type="password", autoComplete="new-password",
                   style={"marginBottom": "12px", "height": "40px"}),
         html.Div("Almeno 10 caratteri, con lettere e numeri. Evita password già usate altrove.",
                  className="pw-hint"),
         dbc.Label("Conferma password", className="form-label"),
         dbc.Input(id="rg-pw2", type="password", autoComplete="new-password",
                   style={"marginBottom": "14px", "height": "40px"})])

    return html.Div([
        dcc.Location(id="rg-url"),
        html.Div([html.Div([
            html.Div(html.Img(src="/assets/logo.png"), className="login-logo"),
            html.H2("Attiva il tuo accesso", className="login-title"),
            html.P("Usa il codice paziente e il codice di attivazione ricevuti dalla struttura.",
                   className="login-sub"),
            html.Div(id="rg-msg"),
            html.Div(id="rg-form", children=[
                dbc.Row([
                    dbc.Col([dbc.Label("Codice paziente", className="form-label"),
                             dbc.Input(id="rg-code", placeholder="PT-XXXXX",
                                       style={"height": "40px", "textTransform": "uppercase"})], md=6),
                    dbc.Col([dbc.Label("Codice di attivazione", className="form-label"),
                             dbc.Input(id="rg-act", placeholder="6 cifre", maxLength=6,
                                       inputMode="numeric", autoComplete="one-time-code",
                                       style={"height": "40px", "letterSpacing": "4px"})], md=6),
                ], className="g-2", style={"marginBottom": "14px"}),
                *email_field,
                html.Div([
                    dbc.Checkbox(id="rg-privacy", value=False,
                                 label="Ho letto l'informativa sul trattamento dei dati personali (obbligatorio)"),
                    html.Div(INFORMATIVA, style={"margin": "6px 0 10px 24px", "color": "#6B7280"}),
                    dbc.Checkbox(id="rg-consent-email", value=False,
                                 label="Desidero ricevere via email conferme e promemoria degli appuntamenti"),
                ], className="consent-box"),
                dbc.Button("Crea account", id="rg-btn", className="btn-pink w-100",
                           style={"height": "46px"}),
            ]),
            html.Div([html.A("← Torna all'accesso", href="/patient/login")], className="auth-links"),
        ], className="login-card", style={"maxWidth": "520px"})], className="login-wrapper"),
    ], style={"margin": "0"})


@callback(
    Output("rg-msg", "children"),
    Output("rg-form", "style"),
    Output("rg-url", "href"),
    Input("rg-btn", "n_clicks"),
    State("rg-code", "value"), State("rg-act", "value"), State("rg-email", "value"),
    State("rg-pw", "value"), State("rg-pw2", "value"),
    State("rg-privacy", "value"), State("rg-consent-email", "value"),
    prevent_initial_call=True,
)
def register(_n, code, act, email, pw, pw2, privacy, consent_email):
    pending = session.get("pending_oauth")            # identità OAuth verificata lato server
    if pending:
        email, pw = pending["email"], None
    elif (pw or "") != (pw2 or ""):
        return dbc.Alert("Le password non coincidono.", color="danger"), dash.no_update, dash.no_update
    try:
        aid, needs_verify = portal_db.register_account(code, act, email, pw, bool(privacy),
                                                       bool(consent_email), oauth=pending)
    except portal_db.PortalError as e:
        audit("patient_register_failed", "anon", detail=f"{(code or '')[:20]}: {e}")
        return dbc.Alert(str(e), color="danger"), dash.no_update, dash.no_update
    audit("patient_registered", "patient", aid, detail=pending["provider"] if pending else "password")
    if needs_verify:
        send_verification(aid)
        session.pop("pending_oauth", None)
        return (dbc.Alert([html.B("Quasi fatto! "),
                           "Ti abbiamo inviato un'email con il link per confermare l'indirizzo. "
                           "Il link scade tra 48 ore."], color="success"),
                {"display": "none"}, dash.no_update)
    from database.db import read_scope
    from database.models import PatientAccount
    with read_scope() as db:
        pid = db.get(PatientAccount, aid).patient_id
    login_patient(aid, pid, f"oauth:{pending['provider']}")
    return "", {"display": "none"}, "/patient/portal"
