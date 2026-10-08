"""Agenda appuntamenti e gestione referti (staff: admin / clinician)."""
from datetime import datetime, date
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from database import portal_db
from auth.session import current_staff
from services.notifications import (send_appointment_confirmation, send_appointment_cancellation,
                                    send_due_reminders)
from services.mailer import smtp_configured
from services.audit import audit
from services.timeutil import local_to_utc, fmt_short, utcnow, local_now
from config import PINK, FACILITY_ADDRESS

dash.register_page(__name__, path="/agenda", name="Agenda & Referti")

APPT_TYPES = ["Prima visita senologica", "Visita di controllo", "Mammografia", "Ecografia mammaria",
              "Risonanza magnetica mammaria", "Agobiopsia ecoguidata", "Visita chirurgica pre-operatoria",
              "Visita anestesiologica", "Intervento chirurgico (ricovero)", "Visita oncologica",
              "Consulenza genetica", "Medicazione / controllo post-operatorio"]
TABLE_STYLE = dict(
    style_table={"borderRadius": "12px", "overflow": "hidden", "border": "1px solid #E5E7EB"},
    style_cell={"textAlign": "left", "padding": "9px 12px", "fontSize": "12px",
                "fontFamily": "Inter,Arial,sans-serif", "border": "none", "borderBottom": "1px solid #F3F4F6",
                "whiteSpace": "normal", "height": "auto"},
    style_header={"backgroundColor": "#EDE7F6", "color": "#4A235A", "fontWeight": "700", "fontSize": "11px",
                  "textTransform": "uppercase", "border": "none"},
    style_as_list_view=True, page_size=12, sort_action="native",
)


def _can_write():
    s = current_staff()
    return bool(s and s.get("role") in ("admin", "clinician")), s


def layout(**kwargs):
    ok, staff = _can_write()
    if not ok:
        return dbc.Alert("Accesso riservato ai clinici e agli amministratori.", color="danger", className="m-4")
    mail_badge = (dbc.Badge("SMTP attivo", color="success") if smtp_configured()
                  else dbc.Badge("SMTP non configurato · email in outbox", color="warning", text_color="dark"))
    pts = portal_db.patient_options()
    return html.Div([
        html.Div([
            html.Div([html.H1("Agenda & Referti", className="page-title"),
                      html.P("Appuntamenti con notifiche email al paziente · pubblicazione referti nel portale",
                             className="page-subtitle")]),
            mail_badge,
        ], className="page-topbar"),
        html.Div([
            dbc.Tabs([
                dbc.Tab(_tab_appointments(pts), label="📅  Appuntamenti", tab_id="appt"),
                dbc.Tab(_tab_documents(pts), label="📁  Referti", tab_id="docs"),
                dbc.Tab(_tab_log(), label="✉️  Notifiche & Audit", tab_id="log"),
            ], active_tab="appt"),
        ], style={"padding": "20px 24px"}),
        dcc.Store(id="ag-refresh"),
    ])


# ── Appuntamenti ──────────────────────────────────────────────────────────────
def _tab_appointments(pts):
    return dbc.Row([
        dbc.Col(html.Div([
            html.Div("Nuovo appuntamento", className="card-title"),
            dbc.Label("Paziente", className="form-label"),
            dcc.Dropdown(id="ag-patient", options=pts, placeholder="Cerca codice…", style={"fontSize": "13px"}),
            html.Div(id="ag-patient-note", style={"fontSize": "11px", "color": "#6B7280", "margin": "4px 0 10px"}),
            dbc.Label("Prestazione", className="form-label"),
            dcc.Dropdown(id="ag-type", options=APPT_TYPES, placeholder="Seleziona…", style={"fontSize": "13px"}),
            dbc.Row([
                dbc.Col([dbc.Label("Data", className="form-label mt-2"),
                         dcc.DatePickerSingle(id="ag-date", min_date_allowed=date.today(),
                                              display_format="DD/MM/YYYY", first_day_of_week=1)], md=6),
                dbc.Col([dbc.Label("Ora", className="form-label mt-2"),
                         dbc.Input(id="ag-time", type="time", value="09:00", style={"height": "40px"})], md=3),
                dbc.Col([dbc.Label("Durata", className="form-label mt-2"),
                         dbc.Select(id="ag-duration", value="30",
                                    options=[{"label": f"{m} min", "value": str(m)} for m in (15, 20, 30, 45, 60, 90, 120)])],
                        md=3),
            ], className="g-2"),
            dbc.Label("Sede", className="form-label mt-2"),
            dbc.Input(id="ag-location", value="Breast Unit — Ambulatorio 1", style={"height": "38px"}),
            dbc.Label("Medico", className="form-label mt-2"),
            dbc.Input(id="ag-clinician", placeholder="Dott./Dott.ssa…", style={"height": "38px"}),
            dbc.Label("Istruzioni per il paziente (visibili nel portale, non in email)",
                      className="form-label mt-2"),
            dbc.Textarea(id="ag-instr", rows=2, style={"fontSize": "13px"}),
            dbc.Checkbox(id="ag-notify", value=True, className="mt-2",
                         label="Invia email di conferma al paziente"),
            dbc.Button("Prenota appuntamento", id="ag-create", className="btn-pink w-100 mt-3"),
            html.Div(id="ag-create-msg", className="mt-2"),
        ], className="card-box"), md=5),
        dbc.Col(html.Div([
            html.Div([html.Span("Prossimi appuntamenti", className="card-title"),
                      dbc.Button("Annulla selezionato", id="ag-cancel", color="danger", outline=True,
                                 size="sm", disabled=True)],
                     style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
            html.Div(id="ag-cancel-msg", className="mb-2"),
            dash_table.DataTable(id="ag-table", columns=[
                {"name": "Data/ora", "id": "when"}, {"name": "Paziente", "id": "patient_code"},
                {"name": "Prestazione", "id": "type"}, {"name": "Sede", "id": "location"},
                {"name": "Conferma", "id": "conf"}, {"name": "Promemoria", "id": "rem"},
                {"name": "Email", "id": "notif"}],
                data=_appt_rows(), row_selectable="single", selected_rows=[], **TABLE_STYLE),
            html.Div("Promemoria: inviato automaticamente il giorno prima (dalle 8:00) ai pazienti con "
                     "account verificato e consenso email.", style={"fontSize": "11px", "color": "#6B7280",
                                                                     "marginTop": "8px"}),
        ], className="card-box"), md=7),
    ], className="g-3 mt-1")


def _appt_rows():
    rows = []
    for a in portal_db.appointments(upcoming_only=True):
        rows.append({"id": a["id"], "when": fmt_short(a["start_at"]), "patient_code": a["patient_code"],
                     "type": a["type"], "location": a["location"],
                     "conf": "✓ " + fmt_short(a["confirmation_sent_at"]) if a["confirmation_sent_at"] else "—",
                     "rem": "✓ " + fmt_short(a["reminder_sent_at"]) if a["reminder_sent_at"] else "in attesa",
                     "notif": "sì" if a["notifiable"] else "no"})
    return rows


@callback(Output("ag-patient-note", "children"), Input("ag-patient", "value"))
def patient_note(pid):
    if not pid:
        return ""
    lbl = next((o["label"] for o in portal_db.patient_options() if o["value"] == pid), "")
    if "portale ✓" in lbl:
        return "Paziente registrato al portale: riceverà le notifiche se ha dato il consenso email."
    return "⚠️ Paziente senza account portale verificato: nessuna email verrà inviata."


@callback(
    Output("ag-create-msg", "children"), Output("ag-table", "data"),
    Input("ag-create", "n_clicks"),
    State("ag-patient", "value"), State("ag-type", "value"), State("ag-date", "date"),
    State("ag-time", "value"), State("ag-duration", "value"), State("ag-location", "value"),
    State("ag-clinician", "value"), State("ag-instr", "value"), State("ag-notify", "value"),
    prevent_initial_call=True,
)
def create_appt(_n, pid, typ, d, t, dur, loc, doc, instr, notify):
    ok, staff = _can_write()
    if not ok:
        return dbc.Alert("Operazione non autorizzata.", color="danger"), dash.no_update
    if not (pid and typ and d and t):
        return dbc.Alert("Compila paziente, prestazione, data e ora.", color="warning"), dash.no_update
    try:
        start_local = datetime.fromisoformat(f"{d[:10]}T{t[:5]}")
        aid = portal_db.create_appointment(int(pid), local_to_utc(start_local), dur, typ,
                                           loc or FACILITY_ADDRESS, doc, instr, staff["username"])
    except (ValueError, portal_db.PortalError) as e:
        return dbc.Alert(str(e), color="danger"), dash.no_update
    audit("appointment_created", "staff", staff["id"], "appointment", aid, f"patient={pid}")
    mail = send_appointment_confirmation(aid) if notify else "non richiesta"
    color = "success" if mail in ("sent", "outbox") else "warning"
    label = {"sent": "inviata ✓", "outbox": "salvata in outbox (SMTP non configurato)"}.get(mail, mail)
    return dbc.Alert(f"Appuntamento prenotato per il {start_local:%d/%m/%Y alle %H:%M}. "
                     f"Email di conferma: {label}.", color=color), _appt_rows()


@callback(Output("ag-cancel", "disabled"), Input("ag-table", "selected_rows"))
def toggle_cancel(sel):
    return not bool(sel)


@callback(
    Output("ag-cancel-msg", "children"), Output("ag-table", "data", allow_duplicate=True),
    Output("ag-table", "selected_rows"),
    Input("ag-cancel", "n_clicks"), State("ag-table", "selected_rows"), State("ag-table", "data"),
    prevent_initial_call=True,
)
def cancel_appt(_n, sel, data):
    ok, staff = _can_write()
    if not (ok and sel):
        return dash.no_update, dash.no_update, dash.no_update
    appt_id = data[sel[0]]["id"]
    if not portal_db.cancel_appointment(appt_id):
        return dbc.Alert("Appuntamento non annullabile.", color="warning"), dash.no_update, []
    audit("appointment_cancelled", "staff", staff["id"], "appointment", appt_id)
    mail = send_appointment_cancellation(appt_id)
    return dbc.Alert(f"Appuntamento annullato. Notifica al paziente: {mail}.", color="info"), _appt_rows(), []


# ── Referti ───────────────────────────────────────────────────────────────────
def _tab_documents(pts):
    return dbc.Row([
        dbc.Col(html.Div([
            html.Div("Nuovo referto", className="card-title"),
            dbc.Label("Paziente", className="form-label"),
            dcc.Dropdown(id="dc-patient", options=pts, placeholder="Cerca codice…", style={"fontSize": "13px"}),
            dbc.Row([
                dbc.Col([dbc.Label("Tipologia", className="form-label mt-2"),
                         dbc.Select(id="dc-cat", value="LAB",
                                    options=[{"label": v, "value": k} for k, v in portal_db.CATEGORY_LABEL.items()])],
                        md=6),
                dbc.Col([dbc.Label("Data referto", className="form-label mt-2"),
                         dcc.DatePickerSingle(id="dc-date", date=date.today(), display_format="DD/MM/YYYY",
                                              first_day_of_week=1)], md=6),
            ], className="g-2"),
            dbc.Label("Titolo", className="form-label mt-2"),
            dbc.Input(id="dc-title", placeholder="es. Emocromo completo", style={"height": "38px"}),
            dbc.Row([
                dbc.Col([dbc.Label("Firmato da", className="form-label mt-2"),
                         dbc.Input(id="dc-author", style={"height": "38px"})], md=6),
                dbc.Col([dbc.Label("Reparto", className="form-label mt-2"),
                         dbc.Input(id="dc-dept", style={"height": "38px"})], md=6),
            ], className="g-2"),
            dbc.Label("Testo / conclusioni", className="form-label mt-2"),
            dbc.Textarea(id="dc-body", rows=4, style={"fontSize": "13px"}),
            dbc.Label("Valori di laboratorio (una riga per esame)", className="form-label mt-2"),
            dbc.Textarea(id="dc-lab", rows=4, style={"fontSize": "12px", "fontFamily": "monospace"},
                         placeholder="Emoglobina; 12.9; g/dL; 12.0 – 16.0; N\nGlicemia; 104; mg/dL; 70 – 100; H"),
            html.Div("Formato: analita ; valore ; unità ; range ; flag (H alto · L basso · N normale)",
                     style={"fontSize": "11px", "color": "#6B7280"}),
            dbc.Row([
                dbc.Col(dbc.Select(id="dc-status", value="final",
                                   options=[{"label": "Definitivo", "value": "final"},
                                            {"label": "Preliminare", "value": "preliminary"}]), md=5),
                dbc.Col(dbc.Checkbox(id="dc-release", value=True, label="Pubblica nel portale paziente"),
                        md=7, style={"paddingTop": "8px"}),
            ], className="g-2 mt-2"),
            dbc.Button("Salva referto", id="dc-save", className="btn-pink w-100 mt-3"),
            html.Div(id="dc-msg", className="mt-2"),
        ], className="card-box"), md=5),
        dbc.Col(html.Div([
            html.Div("Referti del paziente", className="card-title"),
            html.Div("Seleziona un paziente nel modulo per vedere i suoi referti.", id="dc-list",
                     style={"fontSize": "13px", "color": "#6B7280"}),
        ], className="card-box"), md=7),
    ], className="g-3 mt-1")


def _doc_list(pid):
    docs = portal_db.documents(int(pid), released_only=False)
    if not docs:
        return html.Div("Nessun referto.", style={"color": "#9CA3AF"})
    return html.Div([html.Div([
        html.Div([html.Span(d["category_label"], className=f"cat-pill cat-{d['category']}"),
                  html.B(d["title"]),
                  html.Span(f"  ·  {fmt_short(d['issued_at'])[:10]}  ·  {len(d['results'])} valori",
                            className="doc-meta")], style={"flex": "1"}),
        dbc.Switch(id={"type": "dc-rel", "id": d["id"]}, value=d["released"],
                   label="Pubblicato" if d["released"] else "Non pubblicato"),
    ], style={"display": "flex", "alignItems": "center", "padding": "8px 0",
              "borderBottom": "1px solid #F3F4F6"}) for d in docs])


@callback(Output("dc-list", "children"), Input("dc-patient", "value"), Input("ag-refresh", "data"))
def show_docs(pid, _):
    return _doc_list(pid) if pid else "Seleziona un paziente nel modulo per vedere i suoi referti."


@callback(
    Output("dc-msg", "children"), Output("ag-refresh", "data"),
    Input("dc-save", "n_clicks"),
    State("dc-patient", "value"), State("dc-cat", "value"), State("dc-date", "date"),
    State("dc-title", "value"), State("dc-author", "value"), State("dc-dept", "value"),
    State("dc-body", "value"), State("dc-lab", "value"), State("dc-status", "value"),
    State("dc-release", "value"),
    prevent_initial_call=True,
)
def save_doc(_n, pid, cat, d, title, author, dept, body, lab, status, release):
    ok, staff = _can_write()
    if not ok:
        return dbc.Alert("Operazione non autorizzata.", color="danger"), dash.no_update
    if not (pid and title and d):
        return dbc.Alert("Paziente, titolo e data sono obbligatori.", color="warning"), dash.no_update
    issued = local_to_utc(datetime.fromisoformat(d[:10] + "T12:00"))
    rows = portal_db.parse_lab_lines(lab)
    doc_id = portal_db.create_document(int(pid), cat, title.strip(), issued, author, dept, body,
                                       status, bool(release), rows, staff["username"])
    audit("document_created", "staff", staff["id"], "document", doc_id,
          f"patient={pid} released={bool(release)}")
    return dbc.Alert(f"Referto salvato ({len(rows)} valori)."
                     + (" Visibile nel portale." if release else " Non ancora pubblicato."),
                     color="success"), str(utcnow())


@callback(Output("dc-msg", "children", allow_duplicate=True),
          Input({"type": "dc-rel", "id": dash.ALL}, "value"),
          State({"type": "dc-rel", "id": dash.ALL}, "id"),
          prevent_initial_call=True)
def toggle_release(values, ids):
    ok, staff = _can_write()
    trig = dash.ctx.triggered_id
    if not (ok and isinstance(trig, dict)):
        return dash.no_update
    val = values[[i["id"] for i in ids].index(trig["id"])]
    portal_db.set_document_release(trig["id"], bool(val))
    audit("document_release", "staff", staff["id"], "document", trig["id"], str(bool(val)))
    return dbc.Alert("Referto pubblicato nel portale." if val else "Referto ritirato dal portale.",
                     color="info")


# ── Notifiche & audit ─────────────────────────────────────────────────────────
def _tab_log():
    return html.Div([
        html.Div([
            dbc.Button("▶  Esegui ora l'invio promemoria", id="lg-run", className="btn-outline-purple"),
            html.Span(id="lg-run-msg", style={"fontSize": "13px", "marginLeft": "12px"}),
        ], className="mt-3 mb-3"),
        html.Div("Registro email", className="card-title"),
        dash_table.DataTable(id="lg-email", columns=[{"name": n, "id": k} for n, k in [
            ("Data", "created_at"), ("Destinatario", "to"), ("Tipo", "kind"), ("Oggetto", "subject"),
            ("Esito", "status"), ("Errore", "error")]], data=_email_rows(), **TABLE_STYLE),
        html.Div("Audit trail (ultimi 100 eventi)", className="card-title mt-4"),
        dash_table.DataTable(columns=[{"name": n, "id": k} for n, k in [
            ("Quando", "ts"), ("Attore", "actor"), ("Azione", "action"), ("Risorsa", "resource"),
            ("IP", "ip"), ("Dettaglio", "detail")]],
            data=[{**a, "ts": fmt_short(a["ts"])} for a in portal_db.audit_log()], **TABLE_STYLE),
    ])


def _email_rows():
    return [{**e, "created_at": fmt_short(e["created_at"])} for e in portal_db.email_log()]


@callback(Output("lg-run-msg", "children"), Output("lg-email", "data"),
          Input("lg-run", "n_clicks"), prevent_initial_call=True)
def run_reminders(_n):
    ok, staff = _can_write()
    if not ok:
        return "Non autorizzato.", dash.no_update
    res = send_due_reminders(force=True)
    audit("reminders_manual_run", "staff", staff["id"], detail=str(res))
    return (f"Appuntamenti di domani: {res.get('candidates', 0)} · inviati {res.get('sent', 0)} · "
            f"outbox {res.get('outbox', 0)} · saltati {res.get('skipped', 0)} · errori {res.get('failed', 0)}",
            _email_rows())
