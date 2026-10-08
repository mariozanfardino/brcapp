"""Test end-to-end di autenticazione, portale paziente e notifiche.
Esecuzione:  python tests/e2e_portal.py   (usa un DB temporaneo, nessuna email reale)"""
import os, sys, re, glob, json, tempfile, shutil
TMP = tempfile.mkdtemp(prefix="brcapp_e2e_")
os.environ.update(BRCAPP_DB_PATH=os.path.join(TMP, "t.db"), BRCAPP_SECRET_KEY="e2e-secret",
                  BRCAPP_SCHEDULER="0", BRCAPP_BASE_URL="http://localhost:8050",
                  GOOGLE_CLIENT_ID="test-id", GOOGLE_CLIENT_SECRET="test-secret")
for k in ("SMTP_HOST",):
    os.environ.pop(k, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as brc
import config

ok_count = 0
def J(o):
    return json.dumps(o, ensure_ascii=False)
def check(cond, msg):
    global ok_count
    if not cond:
        raise AssertionError("✗ " + msg)
    ok_count += 1
    print("  ✓", msg)

def new_client():
    c = brc.server.test_client()
    c.get("/")
    return c

DEPS = None
def fire(c, output, inputs=None, states=None, changed=None):
    """Esegue una callback Dash come farebbe il browser."""
    global DEPS
    if DEPS is None:
        DEPS = c.get("/_dash-dependencies").get_json()
    dep = next(d for d in DEPS if d["output"] == output)
    vals = {**(inputs or {}), **(states or {})}
    def build(lst):
        return [{"id": x["id"], "property": x["property"],
                 "value": vals.get(f"{x['id']}.{x['property']}")} for x in lst]
    outs = [{"id": o.split(".")[0], "property": o.split(".")[1]}
            for o in output.strip(".").split("...")] if output.startswith("..") else \
        {"id": output.split(".")[0], "property": output.split(".")[1]}
    payload = {"output": output, "outputs": outs, "inputs": build(dep["inputs"]),
               "state": build(dep["state"]),
               "changedPropIds": changed or [f"{x['id']}.{x['property']}" for x in dep["inputs"][:1]]}
    r = c.post("/_dash-update-component", json=payload)
    if r.status_code == 204:
        return None
    check(r.status_code == 200, f"callback {output[:45]} → HTTP 200 (got {r.status_code})")
    return r.get_json()["response"]

def page(c, path, search=""):
    """Renderizza il contenuto della pagina (callback di dash.pages)."""
    out = next(d["output"] for d in fire.__globals__["DEPS"] or c.get("/_dash-dependencies").get_json()
               if "_pages_content" in d["output"])
    r = fire(c, out, {"_pages_location.pathname": path, "_pages_location.search": search})
    return json.dumps(r, ensure_ascii=False)

def route(c, path):
    r = fire(c, "..app-sidebar.children...app-body.children..", {"url.pathname": path})
    return json.dumps(r, ensure_ascii=False)

def outbox(kind):
    return sorted(glob.glob(os.path.join(config.OUTBOX_DIR, f"{kind}_*.eml")), key=os.path.getmtime)

def link_from(eml, pattern):
    raw = open(eml, "rb").read().decode("utf-8", "ignore").replace("=\n", "").replace("=3D", "=")
    return re.search(pattern, raw).group(0)

print("\n1) Controllo accessi")
c = new_client()
check('"href": "/login"' in route(c, "/agenda"), "staff non autenticato → redirect /login")
check('"href": "/patient/login"' in route(c, "/patient/portal"), "paziente non autenticato → redirect /patient/login")
check(c.post("/tasks/reminders").status_code == 403, "/tasks/reminders senza token → 403")
check(c.get("/portal-files/appointment/1.ics").status_code == 401, ".ics senza sessione → 401")
h = c.get("/healthz")
check(h.headers.get("X-Frame-Options") == "DENY" and h.headers.get("X-Content-Type-Options") == "nosniff",
      "header di sicurezza presenti")

print("\n2) Login staff")
r = fire(c, "..login-error.children...login-url.href..",
         {"login-btn.n_clicks": 1}, {"login-user.value": "admin", "login-pass.value": "sbagliata"})
check("non valide" in J(r), "password errata respinta")
r = fire(c, "..login-error.children...login-url.href..",
         {"login-btn.n_clicks": 1}, {"login-user.value": "admin", "login-pass.value": "admin123"})
check(r["login-url"]["href"] == "/", "login admin → redirect dashboard")
check("Agenda" in route(c, "/agenda"), "sessione staff valida: sidebar con Agenda")
check("PT-TEST1" in page(c, "/agenda"), "pagina Agenda mostra i pazienti")
r = route(c, "/patients")
check('"href": "/patient/login"' not in r and "Agenda" in r,
      "REGRESSIONE: /patients da staff non rimanda al login paziente")

print("\n3) Prenotazione appuntamento → email di conferma")
from database.db import read_scope
from database.models import Patient, Appointment, PatientAccount, EmailLog
from services.timeutil import local_now
from datetime import timedelta
with read_scope() as db:
    p1 = db.query(Patient).filter(Patient.code == "PT-TEST1").first().id
    p2 = db.query(Patient).filter(Patient.code == "PT-TEST2").first().id
day = (local_now() + timedelta(days=3)).date().isoformat()
r = fire(c, "..ag-create-msg.children...ag-table.data..", {"ag-create.n_clicks": 1},
         {"ag-patient.value": p1, "ag-type.value": "Visita di controllo", "ag-date.date": day,
          "ag-time.value": "11:15", "ag-duration.value": "30", "ag-location.value": "Ambulatorio 2",
          "ag-clinician.value": "Dott. Test", "ag-instr.value": "Portare referti", "ag-notify.value": True})
check("prenotato" in J(r) and "outbox" in J(r), "appuntamento creato, conferma in outbox")
conf = outbox("appt_confirm")
check(len(conf) == 1, "1 email di conferma generata")
raw = open(conf[-1], "rb").read().decode("utf-8", "ignore")
check("text/calendar" in raw and "appuntamento.ics" in raw, "allegato .ics presente")
check("Visita di controllo" not in raw and "Portare referti" not in raw,
      "email senza dati clinici (minimizzazione GDPR)")
r = fire(c, "..ag-create-msg.children...ag-table.data..", {"ag-create.n_clicks": 2},
         {"ag-patient.value": p2, "ag-type.value": "Visita di controllo", "ag-date.date": day,
          "ag-time.value": "12:00", "ag-duration.value": "30", "ag-location.value": "A",
          "ag-clinician.value": "", "ag-instr.value": "", "ag-notify.value": True})
check("nessun account portale" in J(r), "paziente senza account: nessuna email (motivo esplicito)")

print("\n4) Promemoria del giorno prima")
from services.notifications import send_due_reminders
res = send_due_reminders(force=True)
check(res["outbox"] >= 1, f"promemoria generato per l'appuntamento di domani ({res})")
check(send_due_reminders(force=True)["outbox"] == 0, "seconda esecuzione: nessun duplicato (idempotente)")
token_ok = c.post("/tasks/reminders", headers={"X-Cron-Token": "x"}).status_code
check(token_ok == 403, "cron con token errato → 403")

print("\n5) Login paziente, portale e isolamento dati")
cp = new_client()
r = fire(cp, "..pt-login-error.children...pt-login-url.href..", {"pt-login-btn.n_clicks": 1},
         {"pt-email.value": "maria.rossi.test@example.com", "pt-password.value": "Portale!2026"})
check(r["pt-login-url"]["href"] == "/patient/portal", "login paziente test → portale")
html_portal = page(cp, "/patient/portal")
check("Maria Rossi" in html_portal and "RSSMRA71C54F839K" in html_portal, "Anagrafica visibile")
check("Esame istologico" in html_portal and "Emoglobina" in html_portal, "Cartella clinica con referti e valori")
check("in validazione" not in html_portal, "referto NON rilasciato nascosto al paziente")
check("Visita chirurgica pre-operatoria" in html_portal, "Appuntamenti visibili")
check('"href": "/login"' in route(cp, "/agenda"), "paziente non può accedere alle pagine staff")
with read_scope() as db:
    mine = db.query(Appointment).filter(Appointment.patient_id == p1, Appointment.status == "booked").first().id
    other = db.query(Appointment).filter(Appointment.patient_id == p2).first().id
r = cp.get(f"/portal-files/appointment/{mine}.ics")
check(r.status_code == 200 and b"BEGIN:VCALENDAR" in r.data, ".ics del proprio appuntamento scaricabile")
check(cp.get(f"/portal-files/appointment/{other}.ics").status_code == 404, ".ics di altro paziente → 404")
r = fire(cp, "portal-consent-msg.children", {"portal-consent-email.value": False})
with read_scope() as db:
    check(db.query(PatientAccount).filter(PatientAccount.patient_id == p1).first().consent_email is False,
          "revoca consenso email salvata")
cp.get("/auth/logout")
check('"href": "/patient/login"' in route(cp, "/patient/portal"), "logout: sessione distrutta")

print("\n6) Brute force")
cb = new_client()
for i in range(5):
    fire(cb, "..pt-login-error.children...pt-login-url.href..", {"pt-login-btn.n_clicks": 1},
         {"pt-email.value": "maria.rossi.test@example.com", "pt-password.value": "sbagliata!!1"})
r = fire(cb, "..pt-login-error.children...pt-login-url.href..", {"pt-login-btn.n_clicks": 1},
         {"pt-email.value": "maria.rossi.test@example.com", "pt-password.value": "Portale!2026"})
check("Troppi tentativi" in J(r), "account bloccato dopo 5 tentativi falliti")

print("\n7) Registrazione nuovo paziente + verifica email")
cr = new_client()
base = {"rg-code.value": "PT-TEST2", "rg-email.value": "anna.esposito.test@example.com",
        "rg-pw.value": "AnnaPortale2026", "rg-pw2.value": "AnnaPortale2026",
        "rg-privacy.value": True, "rg-consent-email.value": True}
OUT = "..rg-msg.children...rg-form.style...rg-url.href.."
r = fire(cr, OUT, {"rg-btn.n_clicks": 1}, {**base, "rg-act.value": "000000"})
check("non validi" in J(r), "codice attivazione errato respinto")
r = fire(cr, OUT, {"rg-btn.n_clicks": 1}, {**base, "rg-act.value": "482913", "rg-privacy.value": False})
check("informativa" in J(r), "consenso privacy obbligatorio")
r = fire(cr, OUT, {"rg-btn.n_clicks": 1}, {**base, "rg-act.value": "482913", "rg-pw.value": "corta1",
                                            "rg-pw2.value": "corta1"})
check("10 caratteri" in J(r), "policy password applicata")
r = fire(cr, OUT, {"rg-btn.n_clicks": 1}, {**base, "rg-act.value": "482913"})
check("Quasi fatto" in J(r), "registrazione completata, email di verifica inviata")
r = fire(cr, "..pt-login-error.children...pt-login-url.href..", {"pt-login-btn.n_clicks": 1},
         {"pt-email.value": "anna.esposito.test@example.com", "pt-password.value": "AnnaPortale2026"})
check("confermare" in J(r), "login bloccato finché l'email non è verificata")
link = link_from(outbox("verify")[-1], r"/auth/verify/[A-Za-z0-9_\-\.]+")
check(cr.get(link).headers["Location"].endswith("verified=1"), "link di verifica valido")
r = fire(cr, "..pt-login-error.children...pt-login-url.href..", {"pt-login-btn.n_clicks": 1},
         {"pt-email.value": "anna.esposito.test@example.com", "pt-password.value": "AnnaPortale2026"})
check(r["pt-login-url"]["href"] == "/patient/portal", "login dopo verifica riuscito")
r = fire(new_client(), OUT, {"rg-btn.n_clicks": 1},
         {**base, "rg-act.value": "482913", "rg-email.value": "altra@example.com"})
check("non validi" in J(r), "codice di attivazione monouso (non riutilizzabile)")
check(cr.get("/auth/verify/token-falso").headers["Location"].endswith("error=token"), "token manomesso respinto")

print("\n8) Reset password")
rr = fire(new_client(), "rq-msg.children", {"rq-send.n_clicks": 1}, {"rq-email.value": "inesistente@example.com"})
check("Se l'indirizzo" in J(rr), "risposta neutra per email sconosciuta (no enumerazione)")
cz = new_client()
fire(cz, "rq-msg.children", {"rq-send.n_clicks": 1}, {"rq-email.value": "anna.esposito.test@example.com"})
tok = link_from(outbox("reset")[-1], r"token=[A-Za-z0-9_\-\.]+").split("=", 1)[1]
r = fire(cz, "..rs-msg.children...rs-url.href..", {"rs-save.n_clicks": 1},
         {"rs-token.data": tok, "rs-pw.value": "NuovaPassword2026", "rs-pw2.value": "NuovaPassword2026"})
check(r["rs-url"]["href"].endswith("reset=1"), "password reimpostata")
r = fire(cz, "..rs-msg.children...rs-url.href..", {"rs-save.n_clicks": 1},
         {"rs-token.data": tok, "rs-pw.value": "AltraPassword2026", "rs-pw2.value": "AltraPassword2026"})
check("non più valido" in J(r), "link di reset monouso")

print("\n9) OAuth / OpenID Connect (provider simulato)")
from auth import routes as ar
class FakeClient:
    def __init__(self, info): self.info = info
    def authorize_access_token(self): return {"userinfo": self.info}
orig = ar.oauth.create_client
co = new_client()
with co.session_transaction() as s: s["oauth_audience"] = "patient"
ar.oauth.create_client = lambda name: FakeClient({"sub": "g-123", "email": "maria.rossi.test@example.com",
                                                   "email_verified": True})
r = co.get("/auth/callback/google")
check(r.headers["Location"].endswith("/patient/portal"), "OIDC: paziente esistente collegato e loggato")
with read_scope() as db:
    check(db.query(PatientAccount).filter(PatientAccount.oauth_subject == "g-123").count() == 1,
          "identità OIDC (sub) collegata all'account")
co2 = new_client()
with co2.session_transaction() as s: s["oauth_audience"] = "patient"
ar.oauth.create_client = lambda name: FakeClient({"sub": "g-999", "email": "nuovo@example.com",
                                                   "email_verified": True})
check(co2.get("/auth/callback/google").headers["Location"].endswith("/patient/register?oauth=1"),
      "OIDC: identità sconosciuta → registrazione con codice attivazione")
co3 = new_client()
with co3.session_transaction() as s: s["oauth_audience"] = "staff"
ar.oauth.create_client = lambda name: FakeClient({"sub": "x", "email": "sconosciuto@example.com",
                                                   "email_verified": True})
check("oauth_unknown" in co3.get("/auth/callback/google").headers["Location"],
      "OIDC staff: nessun auto-provisioning")
ar.oauth.create_client = orig

print("\n10) Pagine staff principali")
for path in ["/", "/patients", "/classification", "/statistics", "/xai", "/search", "/admin/pins"]:
    check(len(page(c, path)) > 200, f"render {path}")
r = fire(c, "..search-results.children...search-count.children..", {"btn-search.n_clicks": 1},
         {"search-logic.value": "and", "sf-focal.value": "si"})
check("pazienti" in J(r), "ricerca avanzata con filtro risponde")
with read_scope() as db:
    check(db.query(EmailLog).count() >= 4, "registro email popolato (conferma, promemoria, verifica, reset)")

print("\n11) Scheda paziente (staff)")
r = fire(c, "..modal-patient-detail.is_open...modal-pt-header.children...selected-patient-id.data..."
            "pt-modal-tabs.active_tab...patients-table.active_cell..",
         {"patients-table.active_cell": {"row": 0, "column": 0, "row_id": p1}})
check(r["modal-patient-detail"]["is_open"] is True and r["selected-patient-id"]["data"] == p1,
      "click sulla riga apre la scheda del paziente corretto (row_id)")
r = fire(c, "pt-modal-tab-content.children", {"pt-modal-tabs.active_tab": "vs", "selected-patient-id.data": p1},
         changed=["selected-patient-id.data"])
check("PT-TEST1" in J(r), "prima tab visibile subito all'apertura")
r = fire(c, "..btn-classify-from-pt.disabled...btn-classify-from-pt.title..", {"selected-patient-id.data": p1})
check(r["btn-classify-from-pt"]["disabled"] is True, "pulsante Classifica disabilitato se già classificato")
r = fire(c, "pt-nav.href", {"btn-classify-from-pt.n_clicks": None, "btn-xai-from-pt.n_clicks": 1},
         {"selected-patient-id.data": p1}, changed=["btn-xai-from-pt.n_clicks"])
check(r["pt-nav"]["href"] == f"/xai?pid={p1}", "Vedi XAI porta il paziente selezionato")
r = fire(c, "xai-tabs.active_tab", {"xai-url.search": f"?pid={p1}"})
check(r["xai-tabs"]["active_tab"] == "whatif",
      "XAI apre direttamente il What-If")
r = fire(c, "xai-content.children", {"xai-tabs.active_tab": "whatif", "xai-url.search": f"?pid={p1}", "xai-init.n_intervals": 1})
check(f'"value": {p1}' in J(r), "What-If con paziente preselezionato")
from pages.xai import WI_FEATS, sid
r = fire(c, ".." + "...".join(f"wi-{sid(f)}.value" for f in WI_FEATS) + "..", {"wi-patient-select.value": p1})
check("E4" in J(r) and "50-65" in J(r), "What-If precompilato con i dati del paziente")

r = fire(c, "..wi-result-box.children...wi-sens-chart.figure..", {"btn-wi-calc.n_clicks": 1},
         {"wi-patient-select.value": p1, **{f"wi-{sid(f)}.value": "" for f in WI_FEATS}})
check("CONSERVATIVA" in J(r) or "Mastectomia" in J(r), "What-If calcola la predizione")
from database.models import ClassificationResult
with read_scope() as db:
    clf_id = db.query(ClassificationResult).filter(ClassificationResult.patient_id == p1).first().id
r = fire(c, "local-result.children", {"btn-local-analyze.n_clicks": 1}, {"local-clf-select.value": clf_id})
check("Impatto locale" in J(r) and "PT-TEST1" in J(r), "spiegazione locale anche senza snapshot")

print("\n12) Classificazione")
from ml.weka_bridge import get_classifier, ExportedAdaBoost, run_classification as rc, get_feature_importance
check(isinstance(get_classifier(), ExportedAdaBoost), "attivo il modello BrCaM originale (non il fallback sintetico)")
ref = {"età": "66-75", "fumo": "no", "gravidanza": "si", "familiarità_carcinoma_ovarico": "no",
       "struttura_ghiandolare": "Displasia_fibroadenosa", "rapporto_cuteDX": "Infiltrazione",
       "rapporto_cuteSX": "Retrazione", "rapporto_areola_capezzoloDX": "Regolare",
       "rapporto_areola_capezzoloSX": "Retrazione", "stato_linfonodaleDX": "Adenopatia",
       "stato_linfonodaleSX": "Pacchetto_linfonodale", "biRadsClinico": "E1", "citologia_codifica": "C5",
       "focalità": "si", "ricostruzione": "no"}
lab, pc, pm, _ = rc(ref)
check(lab == "CONSERVATIVA" and abs(pc - 0.923) < 0.001, f"predizione di riferimento = WEKA (P cons {pc:.3f})")
fi = get_feature_importance()
check(fi["ricostruzione"] == 1.0 and fi["stato_linfonodaleDX"] == 0.0,
      "importanza XAI dai pesi reali (ricostruzione max, linfonodi non usati)")
from ml.weka_bridge import FEATURE_NAMES
from pages.classification import _safe_id
FOUT = ".." + "...".join(f"feat-{_safe_id(f)}.value" for f in FEATURE_NAMES) + ".."
r = fire(c, FOUT, {"pt-select.value": p2})
vals = [r[f"feat-{_safe_id(f)}"]["value"] for f in FEATURE_NAMES]
check(all(vals) and "None" not in vals, "REGRESSIONE: precompilazione completa (età, focalità, familiarità)")
dep = next(d for d in DEPS if "result-icon.children" in d["output"])
st = {f"feat-{_safe_id(f)}.value": v for f, v in zip(FEATURE_NAMES, vals)}
r = fire(c, dep["output"], {"btn-classify.n_clicks": 1}, {**st, "pt-select.value": p2, "clf-notes.value": ""})
check(r["result-label"]["children"] in ("BCS (Conservativa)", "Mastectomia"), "classificazione eseguita")
check(r["feat-eta"]["invalid"] is False, "nessun campo segnalato come mancante")
with read_scope() as db:
    check(db.query(ClassificationResult).filter(ClassificationResult.patient_id == p2).count() == 1,
          "classificazione salvata sul paziente")
r = fire(c, dep["output"], {"btn-classify.n_clicks": 2}, {**{k: "" for k in st}, "feat-fumo.value": "si",
                                                           "pt-select.value": None, "clf-notes.value": ""})
check(r["feat-eta"]["invalid"] is True and r["feat-fumo"]["invalid"] is False,
      "campi mancanti evidenziati, quelli compilati no")

print(f"\n✅ {ok_count} verifiche superate\n")
shutil.rmtree(TMP, ignore_errors=True)
