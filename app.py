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
    """80 pazienti demo realistici con schema clinico completo."""
    from database.db import StatisticsRepository, session_scope
    from database.models import Patient, ClinicalRecord, ClassificationResult
    from ml.weka_bridge import FEATURES, CLASS_VALUES
    import random, string
    from datetime import datetime, timedelta

    if StatisticsRepository.get_summary()["total_patients"] > 0:
        return

    print("  🌱  Seed 80 pazienti demo…")
    random.seed(42)

    AGE_RANGES    = FEATURES["età"]
    STRUTTURA     = FEATURES["struttura_ghiandolare"]
    CUTE          = FEATURES["rapporto_cuteDX"]
    AREOLA        = FEATURES["rapporto_areola_capezzoloDX"]
    LINFONO       = FEATURES["stato_linfonodaleDX"]
    BIRADS        = FEATURES["biRadsClinico"]
    SI_NO         = ["si","no"]

    BLOOD_TYPES   = ["A","B","AB","0"]
    HISTOTYPES    = ["Carcinoma duttale infiltrante","Carcinoma lobulare infiltrante",
                     "Carcinoma tubulare","Carcinoma midollare","Carcinoma mucinoso"]
    GRADINGS      = ["G1","G2","G3"]
    STAGES        = ["I","IIA","IIB","IIIA","IIIB","IIIC"]
    ER_VALS       = ["Positivo","Negativo","Borderline"]
    CANCER_SITES  = ["Quadrante supero-esterno","Quadrante supero-interno",
                     "Quadrante infero-esterno","Quadrante infero-interno","Centrale"]
    INJURY_TYPES  = ["Nodulo","Addensamento","Distorsione architetturale","Microcalcificazioni"]
    OP_T          = ["T1","T2","T3","T4"]
    OP_N          = ["N0","N1","N2","N3"]
    PROGRESS      = ["Ottimo","Buono","Discreto","Complicato"]
    COSMETIC      = ["Eccellente","Buono","Accettabile","Scarso"]
    BRA_SIZES     = ["1A","2B","3C","4D","5E"]
    PTOSIS        = ["Assente","Grado I","Grado II","Grado III"]
    SKIN_TROPISM  = ["Normale","Aumentato","Ridotto"]

    with session_scope() as db:
        for i in range(80):
            code    = "PT-" + "".join(random.choices(string.ascii_uppercase+string.digits,k=5))
            created = datetime.utcnow() - timedelta(days=random.randint(30,730))
            disease = random.choices(CLASS_VALUES, weights=[0.62,0.38])[0]
            age_r   = random.choice(AGE_RANGES)
            is_mast = disease == "MASTECTOMIA"

            p = Patient(
                code=code, created_at=created,
                gender="F", nazionalita="Italiana",
                age_range=age_r,
                blood_type=random.choice(BLOOD_TYPES),
                rh_positive=random.choice([True,False]),
                initials=f"P{i+1}",
            )
            db.add(p); db.flush()

            # Feature modello (nominali esatte)
            struttura = random.choice(STRUTTURA)
            cute_dx   = random.choice(CUTE)
            cute_sx   = random.choice(CUTE)
            areola_dx = random.choice(AREOLA)
            areola_sx = random.choice(AREOLA)
            # Mastectomia tende ad avere linfonodi più compromessi
            linfo_opts= (["Adenopatia","Pacchetto_linfonodale","Sospetto_adenopatia"]
                         if is_mast else ["Normale","Sospetto_adenopatia"])
            linfo_dx  = random.choice(linfo_opts)
            linfo_sx  = random.choice(linfo_opts)
            birads    = random.choice(["E4","E5","C4","C5"] if is_mast
                                      else ["E2","E3","E4","C3","C4"])
            citologia = "si" if is_mast else random.choice(["si","no"])
            focalita  = "si" if is_mast and random.random()>.4 else "no"
            ricost    = "si" if is_mast and random.random()>.5 else "no"

            # Antropometrici
            peso    = round(random.gauss(68,13),1)
            altezza = round(random.gauss(163,7),1)
            bmi     = round(peso/((altezza/100)**2),1)
            waist   = round(random.gauss(80,10),1)
            hips    = round(random.gauss(98,10),1)
            whr     = round(waist/hips,2)

            cr = ClinicalRecord(
                patient_id=p.id,
                # Antropometrici
                peso=peso, altezza=altezza, bmi=bmi,
                waist=waist, hips=hips, whr=whr,
                bra_size=random.choice(BRA_SIZES),
                ptosis_degree=random.choice(PTOSIS),
                skin_tropism=random.choice(SKIN_TROPISM),
                # Anamnesi
                fumo=random.choice(SI_NO),
                alcohol=random.choice(SI_NO),
                gravidanza=random.choice(SI_NO),
                familiarita_carcinoma_ovarico=random.choices(SI_NO,weights=[15,85])[0],
                previous_cancer=random.choices(SI_NO,weights=[10,90])[0],
                previous_breast_cancer=random.choices(SI_NO,weights=[8,92])[0],
                previous_chemotherapy=random.choices(SI_NO,weights=[15,85])[0],
                previous_radiotherapy=random.choices(SI_NO,weights=[10,90])[0],
                breast_surgeries=random.choices(SI_NO,weights=[12,88])[0],
                autoimmune_diseases=random.choices(SI_NO,weights=[10,90])[0],
                diabetes=random.choices(SI_NO,weights=[12,88])[0],
                keloids=random.choices(SI_NO,weights=[5,95])[0],
                familial_breast_cancer=random.choices(SI_NO,weights=[20,80])[0],
                brca_mutation=random.choices(SI_NO,weights=[8,92])[0],
                struttura_ghiandolare=struttura,
                # Feature modello imaging
                rapporto_cuteDX=cute_dx,
                rapporto_cuteSX=cute_sx,
                rapporto_areola_capezzoloDX=areola_dx,
                rapporto_areola_capezzoloSX=areola_sx,
                stato_linfonodaleDX=linfo_dx,
                stato_linfonodaleSX=linfo_sx,
                biRadsClinico=birads,
                citologia_codifica=citologia,
                focalita=focalita,
                ricostruzione=ricost,
                # Dati clinici aggiuntivi
                preoperative_chemotherapy=random.choices(SI_NO,weights=[25,75])[0],
                injury_type=random.choice(INJURY_TYPES),
                cancer_site=random.choice(CANCER_SITES),
                tumor_size_mm=round(random.gauss(25,12) if is_mast else random.gauss(18,8),1),
                injuries_number=random.randint(1,3),
                event=random.choices(["Sinistro","Bilaterale","Destro"],weights=[45,10,45])[0],
                dubious_injuries=random.choices(SI_NO,weights=[15,85])[0],
                main_cancer_site=random.choice(CANCER_SITES),
                tumor_in_situ=random.choices(SI_NO,weights=[20,80])[0],
                # Valutazione K. mammella
                histotype=random.choice(HISTOTYPES),
                grading=random.choices(GRADINGS,
                    weights=[20,45,35] if is_mast else [30,45,25])[0],
                clinical_stage=random.choices(STAGES,
                    weights=[10,20,25,25,15,5] if is_mast else [30,30,25,10,4,1])[0],
                er_status=random.choices(ER_VALS,weights=[65,25,10])[0],
                pgr_status=random.choices(ER_VALS,weights=[55,35,10])[0],
                ki67=round(random.gauss(35,15) if is_mast else random.gauss(20,10),1),
                cerbb2=random.choices(["Positivo","Negativo","Equivoco"],weights=[20,70,10])[0],
                classification_pre=random.choice(["Luminale A","Luminale B",
                                                   "HER2-enriched","Triplo negativo"]),
                # Pre/Post
                t_operation_type=random.choice(OP_T),
                n_operation_type=random.choice(OP_N),
                histotype_post=random.choice(HISTOTYPES),
                grading_post=random.choice(GRADINGS),
                clinical_stage_post=random.choice(STAGES),
                er_post=random.choices(ER_VALS,weights=[65,25,10])[0],
                pgr_post=random.choices(ER_VALS,weights=[55,35,10])[0],
                ki67_post=round(random.gauss(20,10),1),
                cerbb2_post=random.choices(["Positivo","Negativo","Equivoco"],weights=[20,70,10])[0],
                classification_post=random.choice(["Luminale A","Luminale B",
                                                    "HER2-enriched","Triplo negativo"]),
                nodal_status_post=linfo_dx,
                surgical_progress=random.choice(PROGRESS),
                cosmetic_result=random.choice(COSMETIC) if not is_mast else "N/A",
                DISEASE=disease,
            )
            db.add(cr)

            c_cons = round(random.uniform(0.65,0.92) if not is_mast
                           else random.uniform(0.05,0.38), 3)
            db.add(ClassificationResult(
                patient_id=p.id,
                run_at=created+timedelta(days=random.randint(1,30)),
                model_version="fallback-1.0",
                predicted_class=disease,
                confidence_bcs=c_cons,
                confidence_mast=round(1-c_cons,3),
            ))

    print("  ✓  80 pazienti demo inseriti con schema clinico completo")

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
