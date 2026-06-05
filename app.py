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
    """Inserisce pazienti fittizi realistici se il DB è vuoto."""
    from database.db import StatisticsRepository, session_scope
    from database.models import Patient, ClinicalRecord, ClassificationResult
    import random, string
    from datetime import datetime, timedelta

    if StatisticsRepository.get_summary()["total_patients"] > 0:
        return

    print("  🌱  Inserimento dati demo…")
    random.seed(42)

    diseases = ["BCS", "BCS", "BCS", "Mastectomy", "BCS", "Mastectomy"]

    with session_scope() as db:
        for i in range(80):
            code = "PT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            created = datetime.utcnow() - timedelta(days=random.randint(0, 365))
            p = Patient(code=code, created_at=created)
            db.add(p); db.flush()

            disease = diseases[i % len(diseases)]

            cr = ClinicalRecord(
                patient_id           = p.id,
                peso                 = round(random.gauss(68, 13), 1),
                altezza              = round(random.gauss(163, 7), 1),
                fumo                 = random.choice([0, 0, 0, 1]),
                gravidanza           = random.choice([0, 1, 1, 1]),
                allattamento         = random.choice([0, 1, 1]),
                menopausa            = random.choice([0, 0, 1, 1]),
                casi_vero_famiglia   = random.choice([0, 0, 0, 1]),
                familiarita_carcinoma_ovario = random.choice([0, 0, 0, 0, 1]),
                struttura_ghiandolare        = round(random.uniform(1, 4), 2),
                rapporto_cuteDX              = round(random.uniform(0.1, 0.9), 3),
                rapporto_cuteSX              = round(random.uniform(0.1, 0.9), 3),
                rapporto_areola_capezzolooDX = round(random.uniform(0.1, 0.8), 3),
                rapporto_areola_capezzoloSX  = round(random.uniform(0.1, 0.8), 3),
                stato_linfonodaleXX          = random.choice([0, 0, 0, 1, 2]) if disease=="Mastectomy" else random.choice([0, 0, 1]),
                stato_linfondaleXX           = random.choice([0, 0, 0, 1, 2]) if disease=="Mastectomy" else random.choice([0, 0, 1]),
                biRadioClinico               = random.choice([3, 3, 4, 4, 5]) if disease=="Mastectomy" else random.choice([3, 3, 4]),
                citologia                    = random.choice([3, 4, 5]) if disease=="Mastectomy" else random.choice([2, 3, 3]),
                citologia_codifica           = random.choice([1, 2]),
                focalita                     = 2 if disease=="Mastectomy" and random.random()>0.5 else 1,
                lato_intervento              = random.choice([0, 1]),
                intervento_chirurgico_bilaterale = 1 if disease=="Mastectomy" and random.random()>0.7 else 0,
                ricostruzione                = random.choice([0, 0, 1]),
                DISEASE                      = disease,
            )
            db.add(cr)

            # Aggiungi alcune classificazioni AI storiche
            n_clf = random.randint(1, 3)
            for j in range(n_clf):
                conf_bcs  = round(random.uniform(0.6, 0.95), 3) if disease=="BCS" else round(random.uniform(0.1, 0.4), 3)
                conf_mast = round(1 - conf_bcs, 3)
                clf_date  = created + timedelta(days=random.randint(1, 30)*(j+1))
                db.add(ClassificationResult(
                    patient_id      = p.id,
                    run_at          = clf_date,
                    model_version   = "fallback-1.0",
                    predicted_class = disease,
                    confidence_bcs  = conf_bcs,
                    confidence_mast = conf_mast,
                ))

    print("  ✓  80 pazienti demo inseriti con classificazioni storiche")
    # Verifica
    from database.db import StatisticsRepository
    s = StatisticsRepository.get_summary()
    print(f"  📊  Verifica DB: {s['total_patients']} pazienti · {s['total_classifications']} classificazioni")


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
                if s.connect_ex(("127.0.0.1", p)) != 0: return p
        return start

    port = int(os.environ.get("PORT", free_port()))
    
    # Render e altri server richiedono 0.0.0.0
    # In locale funziona ugualmente
    app.run(debug=False, host="0.0.0.0", port=port)
