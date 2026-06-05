import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
from database.auth_db import PatientAuthRepository

dash.register_page(__name__, path="/patient/login", name="Accesso Paziente")

layout = html.Div([
    dcc.Location(id="pt-login-url"),
    html.Div([
        html.Div([
            html.Div(html.Img(src="/assets/logo.png"), className="login-logo"),
            html.H2("Area Personale Paziente", className="login-title"),
            html.P("Accedi con il tuo codice paziente e il PIN fornito dal medico",
                   className="login-sub"),

            html.Div(id="pt-login-error", style={"display":"none"}),

            dbc.Label("Codice paziente", className="form-label"),
            dbc.Input(id="pt-code", placeholder="es. PT-A1B2C",
                      style={"marginBottom":"14px","height":"42px",
                             "textTransform":"uppercase"}),

            dbc.Label("PIN (6 cifre)", className="form-label"),
            dbc.Input(id="pt-pin", type="password",
                      placeholder="••••••",
                      maxLength=6,
                      style={"marginBottom":"22px","height":"42px",
                             "letterSpacing":"6px","fontSize":"18px"}),

            dbc.Button("Accedi →", id="pt-login-btn",
                       className="btn-pink w-100",
                       style={"height":"46px","fontSize":"15px"}),

            html.Div([
                "Sei un operatore sanitario? ",
                html.A("Accedi qui", href="/login"),
            ], className="login-toggle"),

        ], className="login-card"),
    ], className="login-wrapper"),
], style={"margin":"0"})


@callback(
    Output("patient-store","data"),
    Output("pt-login-error","children"),
    Output("pt-login-error","style"),
    Output("pt-login-url","href"),
    Input("pt-login-btn","n_clicks"),
    Input("pt-pin","n_submit"),
    State("pt-code","value"),
    State("pt-pin","value"),
    prevent_initial_call=True,
)
def pt_login(n_btn, n_sub, code, pin):
    if not (code and pin):
        return dash.no_update, "Inserisci codice e PIN.", \
               {"display":"block","className":"login-error"}, dash.no_update
    data = PatientAuthRepository.authenticate(code or "", pin or "")
    if not data:
        return dash.no_update, "Codice o PIN non validi. Contatta il tuo medico.", \
               {"display":"block","className":"login-error"}, dash.no_update
    return data, "", {"display":"none"}, "/patient/report"
