import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database import portal_db
from services.notifications import send_password_reset
from services.security import read_token
from services.audit import audit

dash.register_page(__name__, path="/patient/reset", name="Portale Paziente — Password")


def layout(token=None, **kwargs):
    if token:
        body = [
            html.H2("Nuova password", className="login-title"),
            html.P("Scegli una nuova password per il Portale Paziente.", className="login-sub"),
            html.Div(id="rs-msg"),
            dcc.Store(id="rs-token", data=token),
            dbc.Label("Nuova password", className="form-label"),
            dbc.Input(id="rs-pw", type="password", autoComplete="new-password",
                      style={"marginBottom": "12px", "height": "40px"}),
            html.Div("Almeno 10 caratteri, con lettere e numeri.", className="pw-hint"),
            dbc.Label("Conferma password", className="form-label"),
            dbc.Input(id="rs-pw2", type="password", autoComplete="new-password",
                      style={"marginBottom": "18px", "height": "40px"}),
            dbc.Button("Salva password", id="rs-save", className="btn-pink w-100", style={"height": "46px"}),
        ]
    else:
        body = [
            html.H2("Recupero password", className="login-title"),
            html.P("Inserisci l'email del tuo account: riceverai un link valido 60 minuti.",
                   className="login-sub"),
            html.Div(id="rq-msg"),
            dbc.Label("Email", className="form-label"),
            dbc.Input(id="rq-email", type="email", autoComplete="email",
                      style={"marginBottom": "18px", "height": "40px"}),
            dbc.Button("Invia link", id="rq-send", className="btn-pink w-100", style={"height": "46px"}),
        ]
    return html.Div([
        dcc.Location(id="rs-url"),
        html.Div([html.Div([html.Div(html.Img(src="/assets/logo.png"), className="login-logo"), *body,
                            html.Div([html.A("← Torna all'accesso", href="/patient/login")],
                                     className="auth-links")],
                           className="login-card")], className="login-wrapper"),
    ], style={"margin": "0"})


@callback(Output("rq-msg", "children"), Input("rq-send", "n_clicks"),
          State("rq-email", "value"), prevent_initial_call=True)
def request_reset(_n, email):
    aid, _ = portal_db.find_account_by_email(email)
    if aid:
        send_password_reset(aid)
        audit("password_reset_requested", "patient", aid)
    # Stessa risposta in ogni caso: niente enumerazione degli account
    return dbc.Alert("Se l'indirizzo è registrato, riceverai a breve un'email con le istruzioni.",
                     color="info")


@callback(Output("rs-msg", "children"), Output("rs-url", "href"),
          Input("rs-save", "n_clicks"),
          State("rs-token", "data"), State("rs-pw", "value"), State("rs-pw2", "value"),
          prevent_initial_call=True)
def do_reset(_n, token, pw, pw2):
    data = read_token("reset", token or "")
    if not data:
        return dbc.Alert("Link non valido o scaduto. Richiedine uno nuovo.", color="danger"), dash.no_update
    if (pw or "") != (pw2 or ""):
        return dbc.Alert("Le password non coincidono.", color="danger"), dash.no_update
    try:
        portal_db.reset_password(int(data["aid"]), data.get("x", ""), pw or "")
    except portal_db.PortalError as e:
        return dbc.Alert(str(e), color="danger"), dash.no_update
    audit("password_reset_done", "patient", data["aid"])
    return "", "/patient/login?reset=1"
