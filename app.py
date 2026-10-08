"""BrCapp — entry point."""
import os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=os.environ.get("BRCAPP_LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from flask import Flask
import config
import database.db as db_module

# ── Database e dati iniziali ──────────────────────────────────────────────────
db_module.setup(config.DB_PATH)
from database.auth_db import seed_default_users
from services.seed_demo import seed_demo_data, auto_import_csv
from services.seed_test import seed_test_patients
auto_import_csv()            # opt-in: BRCAPP_IMPORT_CSV=1
seed_default_users()
seed_demo_data()
seed_test_patients()

# ── Server Flask: sessione firmata, OAuth/OIDC, route di servizio ─────────────
server = Flask(__name__)
from auth import session as auth_session
from auth.routes import init_oauth
auth_session.configure(server)
init_oauth(server)

app = dash.Dash(__name__, server=server, use_pages=True,
                external_stylesheets=[],   # Bootstrap 5.3.6 servito da assets/ (nessun CDN esterno)
                suppress_callback_exceptions=True, title=config.APP_NAME,
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])

from components.sidebar import sidebar

STAFF_PUBLIC   = {"/login"}
PATIENT_PUBLIC = {"/patient/login", "/patient/register", "/patient/reset"}
PATIENT_AREA   = {"/patient/portal"}

app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="app-sidebar"),
    html.Div(id="app-body"),
])


def _full(content):
    return html.Div(content, style={"marginLeft": "0"})


@callback(Output("app-sidebar", "children"), Output("app-body", "children"),
          Input("url", "pathname"))
def route(pathname):
    """Controllo accessi lato server: l'identità arriva SOLO dalla sessione Flask."""
    pathname = (pathname or "/").rstrip("/") or "/"
    staff = auth_session.current_staff()
    patient = auth_session.current_patient()

    if pathname in STAFF_PUBLIC | PATIENT_PUBLIC:
        return html.Div(), _full(dash.page_container)
    # Attenzione: "/patients" (staff) inizia anch'esso con "/patient" → serve lo slash
    if pathname in PATIENT_AREA or pathname.startswith("/patient/"):
        if not patient:
            return html.Div(), dcc.Location(href="/patient/login", id="redir-pt")
        return html.Div(), _full(dash.page_container)

    # Area staff
    if not staff:
        return html.Div(), dcc.Location(href="/login", id="redir")
    if pathname not in staff.get("permissions", {}).get("pages", ["/"]):
        return sidebar(pathname, staff), html.Div(html.Div([
            html.H2("🚫  Accesso negato"),
            html.P("Il tuo ruolo non ha accesso a questa sezione."),
            html.A("← Dashboard", href="/", style={"color": config.PINK, "fontWeight": "600"}),
        ], className="access-denied"), id="main-content")
    return sidebar(pathname, staff), html.Div(dash.page_container, id="main-content")


# ── Scheduler promemoria (un solo processo: con gunicorn usare 1 worker o il cron) ──
from services import scheduler
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    print(f"\n  🎗  BrCapp {config.APP_VERSION} → http://127.0.0.1:{port}")
    print("  Staff:     admin/admin123 · dott_rossi/clinico123 · viewer/viewer123")
    print("  Paziente:  /patient/login  (vedi README_PORTALE.md per gli account di test)")
    print(f"  OAuth:     {', '.join(config.enabled_providers()) or 'nessun provider configurato'}")
    print(f"  Email:     {'SMTP ' + config.SMTP_HOST if config.SMTP_HOST else 'outbox → ' + config.OUTBOX_DIR}\n")
    app.run(debug=False, host="0.0.0.0", port=port)   # 0.0.0.0 obbligatorio su Render
