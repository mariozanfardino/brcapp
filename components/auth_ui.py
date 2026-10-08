"""Elementi UI condivisi dalle pagine di accesso."""
from dash import html
import dash_bootstrap_components as dbc
from config import enabled_providers

_ICONS = {"google": "G", "microsoft": "▦", "oidc": "🔐"}

MESSAGES = {
    "logout":       ("success", "Sei uscito correttamente."),
    "verified":     ("success", "Email confermata. Ora puoi accedere."),
    "oauth":        ("danger",  "Accesso con provider esterno non riuscito. Riprova."),
    "oauth_unknown":("danger",  "Nessun account staff associato a questa identità. Contatta l'amministratore."),
    "token":        ("danger",  "Link non valido o scaduto."),
    "unverified":   ("warning", "Devi prima confermare il tuo indirizzo email."),
    "disabled":     ("danger",  "Account disabilitato. Contatta la struttura."),
    "reset":        ("success", "Password aggiornata. Ora puoi accedere."),
}

def query_alert(kwargs: dict):
    for key in ("error", "logout", "verified", "reset"):
        val = kwargs.get(key)
        if val:
            code = val if key == "error" else key
            color, text = MESSAGES.get(code, ("danger", "Si è verificato un errore."))
            return dbc.Alert(text, color=color, style={"fontSize": "13px"}, dismissable=True)
    return html.Div()

def oauth_buttons(audience: str):
    providers = enabled_providers()
    if not providers:
        return html.Div()
    btns = [html.A([html.Span(_ICONS.get(k, "🔐"), className="oauth-icon"),
                    f"Continua con {p['label']}"],
                   href=f"/auth/oauth/{k}/{audience}", className="oauth-btn")
            for k, p in providers.items()]
    return html.Div([html.Div(html.Span("oppure"), className="auth-divider"), *btns])
