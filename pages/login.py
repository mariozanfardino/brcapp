import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database.auth_db import UserRepository
from auth.session import login_staff
from components.auth_ui import oauth_buttons, query_alert
from services.audit import audit
from services.security import staff_throttled, staff_failure, staff_success

dash.register_page(__name__, path="/login", name="Login")


def layout(**kwargs):
    return html.Div([
        dcc.Location(id="login-url"),
        html.Div([html.Div([
            html.Div(html.Img(src="/assets/logo.png"), className="login-logo"),
            html.H2("Accesso operatori", className="login-title"),
            html.P("Sistema di supporto decisionale oncologico", className="login-sub"),
            query_alert(kwargs),
            html.Div(id="login-error"),
            dbc.Label("Username", className="form-label"),
            dbc.Input(id="login-user", placeholder="username", type="text", autoComplete="username",
                      style={"marginBottom": "14px", "height": "42px"}),
            dbc.Label("Password", className="form-label"),
            dbc.Input(id="login-pass", placeholder="••••••••", type="password",
                      autoComplete="current-password", style={"marginBottom": "22px", "height": "42px"}),
            dbc.Button("Accedi →", id="login-btn", className="btn-pink w-100",
                       style={"height": "46px", "fontSize": "15px"}),
            oauth_buttons("staff"),
            html.Div([html.Span("Sei un paziente? "), html.A("Vai al Portale Paziente", href="/patient/login")],
                     className="login-toggle"),
            html.Hr(style={"margin": "20px 0 12px"}),
            html.Div([html.Span("Demo: ", style={"color": "#9CA3AF", "fontSize": "12px"}),
                      html.Code("admin / admin123", style={"fontSize": "12px"})],
                     style={"textAlign": "center"}),
        ], className="login-card")], className="login-wrapper"),
    ], style={"margin": "0"})


@callback(
    Output("login-error", "children"),
    Output("login-url", "href"),
    Input("login-btn", "n_clicks"),
    Input("login-pass", "n_submit"),
    State("login-user", "value"),
    State("login-pass", "value"),
    prevent_initial_call=True,
)
def do_login(_n, _s, username, password):
    username = (username or "").strip().lower()
    if not (username and password):
        return dbc.Alert("Inserisci username e password.", color="warning"), dash.no_update
    if staff_throttled(username):
        return dbc.Alert("Troppi tentativi falliti. Riprova tra qualche minuto.", color="danger"), dash.no_update
    user = UserRepository.authenticate(username, password)
    if not user:
        staff_failure(username)
        audit("staff_login_failed", "anon", detail=username)
        return dbc.Alert("Credenziali non valide.", color="danger"), dash.no_update
    staff_success(username)
    login_staff(user, "password")
    audit("staff_login", "staff", user["id"], detail="password")
    return "", "/"
