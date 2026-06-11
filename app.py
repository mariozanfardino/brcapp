import sys, os, webbrowser, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
from config import APP_NAME, DB_PATH
import database.db as db_module

# ── DB setup ──────────────────────────────────────────────────────────────────
db_module.setup(DB_PATH)

# ── Import automatico CSV all'avvio ───────────────────────────────────────────
CSV_PATH = "/home/zanfardino/mnt/dev/BOSP/original_data/patients_attributes_list/global_new.csv"

def seed_demo_data():
    """Seed con le 15 feature nominali esatte del modello Adaboost.model."""
    from database.db import StatisticsRepository, session_scope
    from database.models import Patient, ClassificationResult
    from ml.weka_bridge import FEATURES, CLASS_VALUES
    import random, string
    from datetime import datetime, timedelta

    if StatisticsRepository.get_summary()["total_patients"] > 0:
        return

    print("  🌱  Seed 80 pazienti demo…")
    random.seed(42)

    with session_scope() as db:
        for i in range(80):
            code = "PT-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=5))
            created = datetime.utcnow() - timedelta(days=random.randint(0, 365))
            p = Patient(code=code, created_at=created)
            db.add(p); db.flush()

            # Scelta disease con distribuzione realistica
            disease = random.choices(
                CLASS_VALUES,
                weights=[0.60, 0.40]  # 60% conservativa, 40% mastectomia
            )[0]

            # Classificazione AI coerente con disease
            c_cons = round(random.uniform(0.60,0.92) if disease=="CONSERVATIVA"
                           else random.uniform(0.05,0.40), 3)
            c_mast = round(1 - c_cons, 3)

            for j in range(random.randint(1, 3)):
                db.add(ClassificationResult(
                    patient_id=p.id,
                    run_at=created + timedelta(days=random.randint(1,60)*(j+1)),
                    model_version="fallback-1.0",
                    predicted_class=disease,
                    confidence_bcs=c_cons,
                    confidence_mast=c_mast,
                ))

    print("  ✓  80 pazienti demo inseriti")

def auto_import_csv():
    """
    Importa automaticamente il CSV se:
    - Il file esiste
    - Il DB ha meno pazienti del CSV (nuovi dati disponibili)
    """
    if not os.path.exists(CSV_PATH):
        return

    try:
        from scripts.import_csv import run as import_run, read_csv
        from database.db import StatisticsRepository

        df, _, _ = read_csv(CSV_PATH)
        csv_count = len(df)
        db_count  = StatisticsRepository.get_summary()["total_patients"]

        if db_count >= csv_count:
            print(f"  ✓  DB aggiornato ({db_count} pazienti = CSV)")
            return

        print(f"  ↑  CSV: {csv_count} pazienti  ·  DB: {db_count} — avvio import…")
        # Se DB << CSV: pulisci i demo e reimporta tutto
        if db_count < (csv_count * 0.5):
            from database.db import session_scope
            from database.models import Patient
            with session_scope() as db:
                db.query(Patient).delete()
            print(f"  ✓  DB pulito — reimport completo")
        imported = import_run(CSV_PATH, skip_existing=True, silent=False)
        print(f"  ✓  Import completato: {imported} nuovi pazienti")

    except Exception as e:
        print(f"  ⚠  Import CSV non riuscito: {e}")

auto_import_csv()

# ── Seed utenti default ───────────────────────────────────────────────────────
from database.auth_db import seed_default_users
seed_default_users()
seed_demo_data()

# ── App Dash ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__, use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title=APP_NAME,
)

from components.sidebar import sidebar

PUBLIC_PATHS  = {"/login", "/patient/login"}
PATIENT_PATHS = {"/patient/report", "/patient/login"}

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="session-store",  storage_type="session"),
    dcc.Store(id="patient-store",  storage_type="session"),
    html.Div(id="app-sidebar"),
    html.Div(id="app-body"),
])


@callback(
    Output("app-sidebar","children"),
    Output("app-body","children"),
    Input("url","pathname"),
    Input("session-store","data"),
    Input("patient-store","data"),
)
def route(pathname, user, patient):
    pathname = pathname or "/"

    if pathname in PATIENT_PATHS:
        if pathname == "/patient/login":
            return html.Div(), html.Div(dash.page_container, style={"marginLeft":"0"})
        if not patient:
            return html.Div(), dcc.Location(href="/patient/login", id="redir-pt")
        return html.Div(), html.Div(dash.page_container, style={"marginLeft":"0"})

    if pathname in PUBLIC_PATHS:
        return html.Div(), html.Div(dash.page_container, style={"marginLeft":"0"})

    if not user:
        return html.Div(), dcc.Location(href="/login", id="redir")

    allowed = user.get("permissions",{}).get("pages",["/"])
    admin_p = ["/admin/users","/admin/pins"]
    all_ok  = allowed + (admin_p if user.get("permissions",{}).get("can_manage_users") else [])

    if pathname not in all_ok:
        denied = html.Div([html.Div([
            html.H2("🚫  Accesso negato"),
            html.P("Il tuo ruolo non ha accesso a questa sezione."),
            html.A("← Dashboard", href="/", style={"color":"#D63384","fontWeight":"600"}),
        ], className="access-denied")], id="main-content")
        return sidebar(pathname, user), denied

    return sidebar(pathname, user), html.Div(dash.page_container, id="main-content")


@callback(
    Output("session-store","data","allow_duplicate"),
    Output("patient-store","data","allow_duplicate"),
    Output("url","href","allow_duplicate"),
    Input("url","pathname"),
    prevent_initial_call=True,
)
def handle_logout(pathname):
    if pathname == "/logout":         return None, None, "/login"
    if pathname == "/patient/logout": return no_update, None, "/patient/login"
    return no_update, no_update, no_update


if __name__ == "__main__":
    import socket
    def free_port(start=8050):
        for p in range(start, start+20):
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1",p)) != 0: return p
        return start

    port = free_port()
    threading.Thread(
        target=lambda: (__import__("time").sleep(1.2),
                        __import__("webbrowser").open(f"http://127.0.0.1:{port}")),
        daemon=True).start()

    print(f"\n  🎗  BrCapp → http://127.0.0.1:{port}")
    print(f"  Staff:    admin/admin123  ·  dott_rossi/clinico123  ·  viewer/viewer123")
    print(f"  Paziente: /patient/login\n")
    # Su Render HOST non viene letto — forza sempre 0.0.0.0
    app.run(debug=False, host="0.0.0.0", port=port)
