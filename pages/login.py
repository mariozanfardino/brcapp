import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database.auth_db import UserRepository

dash.register_page(__name__, path="/login", name="Login")

layout = html.Div([
    dcc.Location(id="login-url"),
    html.Div([
        html.Div([
            # Logo
            html.Div(html.Img(src="/assets/logo.png"), className="login-logo"),
            html.H2("Accedi a BrCapp", className="login-title"),
            html.P("Sistema di supporto decisionale oncologico",
                   className="login-sub"),

            # Error
            html.Div(id="login-error", style={"display":"none"}),

            # Form
            dbc.Label("Username", className="form-label"),
            dbc.Input(id="login-user", placeholder="username",
                      type="text", style={"marginBottom":"14px","height":"42px"}),

            dbc.Label("Password", className="form-label"),
            dbc.Input(id="login-pass", placeholder="••••••••",
                      type="password", style={"marginBottom":"22px","height":"42px"}),

            dbc.Button("Accedi →", id="login-btn",
                       className="btn-pink w-100",
                       style={"height":"46px","fontSize":"15px"}),

            html.Hr(style={"margin":"24px 0 16px"}),
            html.Div([
                html.Span("Credenziali demo: ", style={"color":"#9CA3AF","fontSize":"12px"}),
                html.Code("admin / admin123",
                          style={"fontSize":"12px","background":"#F4F6F9",
                                 "padding":"2px 8px","borderRadius":"4px"}),
            ], style={"textAlign":"center"}),
        ], className="login-card"),
    ], className="login-wrapper"),
], style={"margin":"0"})


@callback(
    Output("session-store","data"),
    Output("login-error","children"),
    Output("login-error","style"),
    Output("login-url","href"),
    Input("login-btn","n_clicks"),
    Input("login-pass","n_submit"),
    State("login-user","value"),
    State("login-pass","value"),
    prevent_initial_call=True,
)
def do_login(n_btn, n_submit, username, password):
    if not (username and password):
        return dash.no_update, "Inserisci username e password.", \
               {"display":"block"}, dash.no_update
    user = UserRepository.authenticate(username or "", password or "")
    if not user:
        return dash.no_update, "Credenziali non valide. Riprova.", \
               {"display":"block", "className":"login-error"}, dash.no_update
    return user, "", {"display":"none"}, "/"
