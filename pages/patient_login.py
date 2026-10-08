import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database import portal_db
from auth.session import login_patient
from components.auth_ui import oauth_buttons, query_alert
from services.audit import audit

dash.register_page(__name__, path="/patient/login", name="Portale Paziente — Accesso")


def layout(**kwargs):
    return html.Div([
        dcc.Location(id="pt-login-url"),
        html.Div([html.Div([
            html.Div(html.Img(src="/assets/logo.png"), className="login-logo"),
            html.H2("Portale Paziente", className="login-title"),
            html.P("Anagrafica, referti e appuntamenti in un unico posto", className="login-sub"),
            query_alert(kwargs),
            html.Div(id="pt-login-error"),
            dbc.Label("Email", className="form-label"),
            dbc.Input(id="pt-email", type="email", placeholder="nome@esempio.it", autoComplete="email",
                      style={"marginBottom": "14px", "height": "42px"}),
            dbc.Label("Password", className="form-label"),
            dbc.Input(id="pt-password", type="password", placeholder="••••••••",
                      autoComplete="current-password", style={"marginBottom": "20px", "height": "42px"}),
            dbc.Button("Accedi →", id="pt-login-btn", className="btn-pink w-100",
                       style={"height": "46px", "fontSize": "15px"}),
            html.Div([html.A("Primo accesso? Registrati", href="/patient/register"),
                      html.A("Password dimenticata?", href="/patient/reset")], className="auth-links"),
            oauth_buttons("patient"),
            html.Div([html.Span("Sei un operatore sanitario? "), html.A("Accedi qui", href="/login")],
                     className="login-toggle"),
        ], className="login-card")], className="login-wrapper"),
    ], style={"margin": "0"})


@callback(
    Output("pt-login-error", "children"),
    Output("pt-login-url", "href"),
    Input("pt-login-btn", "n_clicks"),
    Input("pt-password", "n_submit"),
    State("pt-email", "value"),
    State("pt-password", "value"),
    prevent_initial_call=True,
)
def pt_login(_n, _s, email, password):
    if not (email and password):
        return dbc.Alert("Inserisci email e password.", color="warning"), dash.no_update
    try:
        aid, pid = portal_db.authenticate(email, password)
    except portal_db.PortalError as e:
        audit("patient_login_failed", "anon", detail=(email or "")[:80])
        return dbc.Alert(str(e), color="danger"), dash.no_update
    login_patient(aid, pid, "password")
    audit("patient_login", "patient", aid, detail="password")
    return "", "/patient/portal"
